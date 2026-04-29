import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import EvalRequest, EvalOut
from app.services.ragas_service import run_rag_eval
from app.services.eval_service import compute_trustworthiness, grade, build_results_payload
from app.services.langsmith_service import ensure_dataset, log_experiment
from app.services.injection_service import run_injection_suite
import app.models as models

router = APIRouter()
logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


@router.post("/run", response_model=EvalOut, summary="Run a full evaluation")
def run_evaluation(req: EvalRequest, db: Session = Depends(get_db)):
    """
    Full evaluation pipeline:

    1. RAGAS metrics  — Faithfulness, AnswerRelevancy, ContextPrecision,
                        ContextRecall, FactualCorrectness, NoiseSensitivity
    2. Injection test — 6-category prompt injection attack suite
                        (only when run_injection=true)
    3. Trustworthiness composite score + letter grade
    4. LangSmith tracking (optional)
    5. Persist + return results

    Set `run_injection: false` to skip the injection suite (much faster).
    """
    # ── 1. RAGAS evaluation ──────────────────────────────────────────────────
    try:
        ragas_scores = run_rag_eval(req.samples, model_name=req.model_name)
    except EnvironmentError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("RAGAS evaluation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"RAGAS evaluation error: {exc}")

    # ── 2. Injection test (optional) ────────────────────────────────────────
    if req.run_injection:
        from langchain_ollama import ChatOllama

        def _injection_target(prompt: str) -> str:
            return ChatOllama(
                model=req.model_name,
                base_url=OLLAMA_BASE_URL,
                temperature=0,
            ).invoke(prompt).content

        try:
            injection_full    = run_injection_suite(_injection_target)
            injection_summary = injection_full["summary"]
        except Exception as exc:
            logger.warning("Injection suite failed, using default: %s", exc)
            injection_summary = {
                "injection_rate": 0.0,
                "robustness":     1.0,
                "status":         f"error: {exc}",
            }
    else:
        injection_summary = {
            "injection_rate": 0.0,
            "robustness":     1.0,
            "status":         "skipped",
        }

    # ── 3. Trustworthiness composite ────────────────────────────────────────
    trust_score = compute_trustworthiness(ragas_scores, injection_summary)
    trust_grade = grade(trust_score)

    # ── 4. LangSmith tracking (optional) ────────────────────────────────────
    ls_dataset_name = ensure_dataset(
        name=f"evalforge-{req.experiment_name}",
        samples=req.samples,
    )
    ls_result = log_experiment(
        experiment_name=req.experiment_name,
        dataset_name=ls_dataset_name,
        target_fn=lambda inputs: {"answer": inputs.get("question", "")},
        ragas_scores=ragas_scores,
        metadata={"model": req.model_name, "agent_type": req.agent_type},
    )

    # ── 5. Build + persist results ───────────────────────────────────────────
    results = build_results_payload(ragas_scores, injection_summary, trust_score, trust_grade)
    if ls_result:
        results["langsmith"] = ls_result

    exp = models.Experiment(
        name=req.experiment_name,
        model_name=req.model_name,
        agent_type=req.agent_type,
        results=results,
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)

    return EvalOut(experiment_id=exp.id, results=exp.results)


@router.get("/{experiment_id}", summary="Get evaluation results by experiment ID")
def get_evaluation(experiment_id: int, db: Session = Depends(get_db)):
    exp = db.query(models.Experiment).filter(models.Experiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp
