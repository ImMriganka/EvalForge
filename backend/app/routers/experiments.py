from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ExperimentOut
import app.models as models

router = APIRouter()


@router.get("/", summary="List all experiments")
def list_experiments(db: Session = Depends(get_db)):
    return db.query(models.Experiment).order_by(models.Experiment.created_at.desc()).all()


@router.get("/{experiment_id}", response_model=ExperimentOut, summary="Get experiment by ID")
def get_experiment(experiment_id: int, db: Session = Depends(get_db)):
    exp = db.query(models.Experiment).filter(models.Experiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp
