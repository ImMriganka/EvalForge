from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String, unique=True, nullable=False)
    description = Column(String, default="")
    created_at  = Column(DateTime, server_default=func.now())
    # List of dicts: {question, contexts, answer, ground_truth}
    samples     = Column(JSON, default=list)


class Experiment(Base):
    __tablename__ = "experiments"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String, nullable=False)
    dataset_id  = Column(Integer, ForeignKey("datasets.id"), nullable=True)
    model_name  = Column(String, nullable=False)
    agent_type  = Column(String, nullable=False)   # "rag" | "react" | "plan_execute"
    created_at  = Column(DateTime, server_default=func.now())
    # Stores RAGAS scores, injection summary, trustworthiness composite
    results     = Column(JSON, default=dict)


class InjectionResult(Base):
    __tablename__ = "injection_results"

    id              = Column(Integer, primary_key=True, index=True)
    experiment_id   = Column(Integer, ForeignKey("experiments.id"), nullable=True)
    attack_category = Column(String, nullable=False)
    prompt          = Column(String, nullable=False)
    response        = Column(String, nullable=False)
    injected        = Column(Integer, default=0)   # 0 or 1
    created_at      = Column(DateTime, server_default=func.now())
