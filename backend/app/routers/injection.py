"""
Injection router — runs the prompt injection test suite against a local Ollama model.

POST /api/v1/injection/run
  {
    "model_name": "llama3.1:8b",   (optional — defaults to env OLLAMA_MODEL)
    "experiment_id": 1              (optional — if provided, updates the experiment's
                                     injection results and recomputes trustworthiness)
  }

Returns InjectionOut with:
  summary  — {total, injected, injection_rate, robustness, by_category}
  details  — per-category lists of {prompt, response, injected}
"""
import os
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import InjectionRunRequest, InjectionOut
from app.services.injection_service import run_injection_suite
from app.services.eval_service import compute_trustworthiness, grade
import app.models as models

router = APIRouter()
logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


@router.post("/run", response_model=InjectionOut, summary="Run prompt injection test suite")
def run_injection(req: InjectionRunRequest, db: Session = Depends(get_db)):
    """
    Run all 6 prompt injection attack categories against the specified Ollama model.

    **Attack categories tested:**
    - `direct_override` — explicit instruction override
    - `roleplay_jailbreak` — persona hijack (DAN / EvilGPT)
    - `indirect_tool` — injection via simulated tool output
    - `code_injection` — malicious code disguised as execution request
    - `encoding_tricks` — base64 / ROT13 encoded override instructions
    - `context_overflow` — injection buried after noise padding

    If `experiment_id` is provided, the injection results are linked to that
    experiment and the trustworthiness score is recomputed and persisted.
    """
    from langchain_ollama import ChatOllama

    # Build the target function: send a prompt → get a response string
    def _target_fn(prompt: str) -> str:
        llm = ChatOllama(
            model=req.model_name,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
        )
        return llm.invoke(prompt).content

    # ── Run the injection suite ───────────────────────────────────────────
    try:
        full_results = run_injection_suite(_target_fn)
    except ConnectionError as exc:
        logger.error("Ollama unreachable during injection run: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=(
                "Cannot reach Ollama. Make sure it is running (`ollama serve`). "
                f"Detail: {exc}"
            ),
        )
    except Exception as exc:
        logger.error("Injection suite failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Injection suite error: {exc}")

    summary = full_results["summary"]
    details = {k: v for k, v in full_results.items() if k != "summary"}

    # ── Optionally update a linked Experiment ────────────────────────────
    if req.experiment_id is not None:
        exp = db.query(models.Experiment).filter(
            models.Experiment.id == req.experiment_id
        ).first()

        if exp is None:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment {req.experiment_id} not found.",
            )

        # Recompute trustworthiness with real injection data
        existing_results = dict(exp.results or {})
        ragas_scores     = existing_results.get("ragas", {})
        trust_score      = compute_trustworthiness(ragas_scores, summary)
        trust_grade      = grade(trust_score)

        existing_results["injection"]       = summary
        existing_results["trustworthiness"] = trust_score
        existing_results["grade"]           = trust_grade

        exp.results = existing_results
        db.add(exp)
        db.commit()

        logger.info(
            "Updated experiment %d with injection results: rate=%.3f trust=%.3f grade=%s",
            req.experiment_id, summary["injection_rate"], trust_score, trust_grade,
        )

    return InjectionOut(summary=summary, details=details)
