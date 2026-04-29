"""
Agent router — dispatches to ReAct or Plan-Execute LangGraph agents.

POST /api/v1/agents/run
  {"question": "...", "agent_type": "react" | "plan_execute", "model_name": "llama3.1:8b"}

Returns AgentRunOut with answer, tool_calls, latency, token counts,
and (for plan_execute) the full plan + step_results for observability.
"""
import logging

from fastapi import APIRouter, HTTPException

from app.schemas import AgentRunRequest, AgentRunOut
from app.services.react_agent import run_react_agent
from app.services.plan_execute_agent import run_plan_execute_agent

router = APIRouter()
logger = logging.getLogger(__name__)

_VALID_AGENT_TYPES = {"react", "plan_execute"}


@router.post("/run", response_model=AgentRunOut, summary="Run a LangGraph agent")
def run_agent(req: AgentRunRequest):
    """
    Run a question through a LangGraph agent and return the answer with
    full observability: tool calls made, latency, token usage.

    **agent_type options:**
    - `react` — ReAct loop: reasons and calls tools iteratively until it has
      an answer. Good for open-ended questions that may need 1–3 tool calls.
    - `plan_execute` — Plan-and-Execute: first decomposes the question into
      steps, executes each step (with optional tool use), then synthesizes.
      Good for multi-hop questions requiring structured reasoning.

    **Example request:**
    ```json
    {
      "question": "What is 25 * 48, and what year is it?",
      "agent_type": "react",
      "model_name": "llama3.1:8b"
    }
    ```
    """
    if req.agent_type not in _VALID_AGENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid agent_type '{req.agent_type}'. "
                   f"Must be one of: {sorted(_VALID_AGENT_TYPES)}",
        )

    try:
        if req.agent_type == "react":
            result = run_react_agent(req.question, model_name=req.model_name)
        else:
            result = run_plan_execute_agent(req.question, model_name=req.model_name)

    except ConnectionError as exc:
        logger.error("Ollama connection failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=(
                f"Cannot reach Ollama at the configured URL. "
                f"Make sure Ollama is running (`ollama serve`). Detail: {exc}"
            ),
        )
    except Exception as exc:
        logger.error("Agent run failed (%s): %s", req.agent_type, exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Agent error ({req.agent_type}): {exc}",
        )

    return AgentRunOut(**result)
