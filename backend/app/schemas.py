from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime


# ── Dataset ──────────────────────────────────────────────────────────────────

class DatasetCreate(BaseModel):
    name: str
    description: str = ""
    samples: list[dict[str, Any]] = Field(
        default=[],
        description="List of {question, contexts, answer, ground_truth} dicts",
    )


class DatasetOut(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime
    sample_count: int

    model_config = {"from_attributes": True}


# ── Eval ─────────────────────────────────────────────────────────────────────

class EvalSample(BaseModel):
    """
    One evaluation sample. Both naming conventions are accepted:
      question / user_input       — the question posed to the LLM
      contexts / retrieved_contexts — list of retrieved document chunks
      answer   / response         — the LLM's answer
      ground_truth / reference    — the correct answer for comparison
    """
    question:           str | None = None
    user_input:         str | None = None
    contexts:           list[str] = Field(default_factory=list)
    retrieved_contexts: list[str] = Field(default_factory=list)
    answer:             str | None = None
    response:           str | None = None
    ground_truth:       str | None = None
    reference:          str | None = None


class EvalRequest(BaseModel):
    experiment_name: str
    model_name: str = "llama3.1:8b"
    agent_type: str = Field(
        "rag",
        description="One of: rag | react | plan_execute",
    )
    samples: list[EvalSample]
    run_injection: bool = True


class EvalOut(BaseModel):
    experiment_id: int
    results: dict[str, Any]


# ── Agent ────────────────────────────────────────────────────────────────────

class AgentRunRequest(BaseModel):
    question: str
    model_name: str = "llama3.1:8b"
    agent_type: str = Field("react", description="react | plan_execute")


class AgentRunOut(BaseModel):
    answer: str
    tool_calls: list[dict[str, Any]] = []
    num_steps: int
    latency_s: float
    total_tokens: int


# ── Experiment ───────────────────────────────────────────────────────────────

class ExperimentOut(BaseModel):
    id: int
    name: str
    model_name: str
    agent_type: str
    created_at: datetime
    results: dict[str, Any]

    model_config = {"from_attributes": True}


# ── Injection ────────────────────────────────────────────────────────────────

class InjectionRunRequest(BaseModel):
    model_name: str = "llama3.1:8b"
    experiment_id: int | None = None


class InjectionOut(BaseModel):
    summary: dict[str, Any]
    details: dict[str, Any]
