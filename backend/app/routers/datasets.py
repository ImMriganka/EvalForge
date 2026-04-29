from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import DatasetCreate, DatasetOut
import app.models as models

router = APIRouter()


@router.get("/", summary="List all datasets")
def list_datasets(db: Session = Depends(get_db)):
    datasets = db.query(models.Dataset).all()
    return [
        DatasetOut(
            id=d.id,
            name=d.name,
            description=d.description,
            created_at=d.created_at,
            sample_count=len(d.samples or []),
        )
        for d in datasets
    ]


@router.post("/", response_model=DatasetOut, status_code=201, summary="Create a dataset")
def create_dataset(body: DatasetCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Dataset).filter(models.Dataset.name == body.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Dataset '{body.name}' already exists")

    dataset = models.Dataset(
        name=body.name,
        description=body.description,
        samples=body.samples,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return DatasetOut(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        created_at=dataset.created_at,
        sample_count=len(dataset.samples or []),
    )


@router.get("/{dataset_id}", summary="Get a dataset by ID")
def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset
