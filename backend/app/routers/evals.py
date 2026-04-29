from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import EvalRequest, EvalOut
import app.models as models

router = APIRouter()


@router.post("/run", response_model=EvalOut, summary="Run a full evaluation")
def run_evaluation(req: EvalRequest, db: Session = Depends(get_db)):
    """
    Phase 2 will implement RAGAS + injection + trustworthiness composite.
    Returns a stub experiment record for now.
    """
    exp = models.Experiment(
        name=req.experiment_name,
        model_name=req.model_name,
        agent_type=req.agent_type,
        results={"status": "not implemented — Phase 2"},
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
