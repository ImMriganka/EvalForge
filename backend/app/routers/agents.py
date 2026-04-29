from fastapi import APIRouter
from app.schemas import AgentRunRequest, AgentRunOut

router = APIRouter()


@router.post("/run", response_model=AgentRunOut, summary="Run a LangGraph agent")
def run_agent(req: AgentRunRequest):
    """
    Phase 3 will wire in the ReAct and Plan-Execute LangGraph agents.
    Returns a stub response for now.
    """
    return AgentRunOut(
        answer="[Phase 3 not yet implemented]",
        tool_calls=[],
        num_steps=0,
        latency_s=0.0,
        total_tokens=0,
    )
