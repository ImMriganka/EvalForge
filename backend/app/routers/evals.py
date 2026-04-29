import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import EvalRequest, EvalOut
from app.services.ragas_service import run_rag_eval
from app.services.eval_service import compute_trustworthiness, grade, build_results_payload
from app.services.langsmith_service import ensure_dataset, log_experiment
import app.models as models

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/run", response_model=EvalOut, summary="Run a full evaluation")
def run_evaluation(req: EvalRequest, db: Session = Depends(get_db)):
    """
    Full RAG evaluation pipeline:

    1. Run RAGAS metrics (Faithfulness, AnswerRelevancy, ContextPrecision,
       ContextRecall, FactualCorrectness, NoiseSensitivity)
    2. Compute trustworthiness composite score + letter grade
    3. Optionally upload dataset + log scores to LangSmith
    4. Persist Experiment record to DB
    5. Return experiment_id + full results payload

    Sample payload:
    {
      "experiment_name": "my-rag-v1",
      "model_name": "gpt-4o-mini",
      "agent_type": "rag",
      "samples": [
        {
          "question": "What is the capital of France?",
          "contexts": ["Paris is the capital of France."],
          "answer": "The capital of France is Paris.",
          "ground_truth": "Paris"
        }
      ],
      "run_injection": false
    }
    """
    # ── 1. RAGAS evaluation ──────────────────────────────────────────────────
    try:
        ragas_scores = run_rag_eval(req.samples, model_name=req.model_name)
    except EnvironmentError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("RAGAS evaluation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"RAGAS evaluation error: {exc}")

    # ── 2. Trustworthiness composite ────────────────────────────────────────
    # Injection summary is empty at this phase — Phase 4 will populate it.
    injection_summary = {"injection_rate": 0.0, "robustness": 1.0, "status": "not_run"}
    trust_score = compute_trustworthiness(ragas_scores, injection_summary)
    trust_grade = grade(trust_score)

    # ── 3. LangSmith tracking (optional — degrades gracefully if key absent) ─
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

    # ── 4. Build + persist results ───────────────────────────────────────────
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
