"""
Plan-and-Execute agent using LangGraph StateGraph.

Unlike ReAct (which loops reactively), Plan-Execute explicitly:
  1. PLANS: breaks the question into ordered steps
  2. EXECUTES: runs each step in sequence, optionally using tools
  3. SYNTHESIZES: combines all step results into a final answer

This is better than ReAct for:
  - Multi-hop questions requiring structured reasoning
  - Tasks where you want full observability into the reasoning chain
  - Questions that benefit from parallelisable sub-tasks

Architecture:
  User question
       │
       ▼
  [Planner] → produces plan = ["step1", "step2", ...]
       │
       ▼
  [Executor] → runs current step, may call tools
       │
       ├─ more steps? ──→ [Executor] (loop)
       │
       └─ done? ──→ [Synthesizer] → final answer
"""
import os
import time
import logging
from typing import Any
from typing_extensions import TypedDict, NotRequired

from langchain_ollama import ChatOllama
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, START, END

from app.services.agent_tools import ALL_TOOLS

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL",    "llama3.1:8b")


# ── State definition ─────────────────────────────────────────────────────────

class PlanExecuteState(TypedDict):
    input:        str            # the original user question
    plan:         list[str]      # ordered list of step descriptions
    step_index:   int            # which step we're currently executing
    step_results: list[str]      # accumulated results from executed steps
    final_answer: NotRequired[str]  # set by synthesizer, absent until then


# ── Node factories ────────────────────────────────────────────────────────────

def _make_planner(llm: ChatOllama):
    def planner(state: PlanExecuteState) -> dict:
        """Decompose the question into 2–4 numbered steps."""
        prompt = (
            "You are a planning assistant. Break the following question into "
            "2 to 4 concrete, ordered steps. Return ONLY a numbered list, "
            "one step per line, no extra commentary.\n\n"
            f"Question: {state['input']}"
        )
        response = llm.invoke([{"role": "user", "content": prompt}])
        lines = [ln.strip() for ln in response.content.strip().splitlines() if ln.strip()]
        # Strip leading "1. " / "2." / "- " numbering
        steps = []
        for ln in lines:
            clean = ln.lstrip("0123456789.-) ").strip()
            if clean:
                steps.append(clean)

        logger.info("Planner produced %d steps for: %s", len(steps), state["input"][:60])
        return {"plan": steps, "step_index": 0, "step_results": []}

    return planner


def _make_executor(llm: ChatOllama, tools: list[BaseTool]):
    tool_map = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)

    def executor(state: PlanExecuteState) -> dict:
        """Execute the current step, using tools if needed."""
        step = state["plan"][state["step_index"]]

        # Build context from previous step results
        prev = "\n".join(
            f"Step {i + 1} result: {r}"
            for i, r in enumerate(state["step_results"])
        ) or "None yet."

        prompt = (
            f"Previous step results:\n{prev}\n\n"
            f"Now execute this step: {step}\n"
            "Use the calculator tool for math. "
            "Use search_web for factual lookups. "
            "Return a concise result for this step only."
        )

        response = llm_with_tools.invoke([{"role": "user", "content": prompt}])
        step_output = response.content or ""

        # Execute any tool calls the LLM made
        if response.tool_calls:
            tool_outputs = []
            for tc in response.tool_calls:
                tool_fn = tool_map.get(tc["name"])
                if tool_fn:
                    try:
                        tool_result = tool_fn.invoke(tc["args"])
                        tool_outputs.append(f"[{tc['name']}({tc['args']})] → {tool_result}")
                    except Exception as exc:
                        tool_outputs.append(f"[{tc['name']}] error: {exc}")
            if tool_outputs:
                step_output = (step_output + "\n" + "\n".join(tool_outputs)).strip()

        logger.info("Executor step %d/%d: %s", state["step_index"] + 1, len(state["plan"]), step[:50])
        return {
            "step_results": state["step_results"] + [step_output],
            "step_index":   state["step_index"] + 1,
        }

    return executor


def _should_continue(state: PlanExecuteState) -> str:
    """Route: loop back to executor if more steps remain, else go to synthesizer."""
    if state["step_index"] < len(state["plan"]):
        return "execute"
    return "synthesize"


def _make_synthesizer(llm: ChatOllama):
    def synthesizer(state: PlanExecuteState) -> dict:
        """Combine all step results into a final, complete answer."""
        steps_text = "\n".join(
            f"Step {i + 1} ({state['plan'][i]}): {r}"
            for i, r in enumerate(state["step_results"])
        )
        prompt = (
            f"Original question: {state['input']}\n\n"
            f"Results from each step:\n{steps_text}\n\n"
            "Write a concise, complete final answer based on the step results above."
        )
        response = llm.invoke([{"role": "user", "content": prompt}])
        return {"final_answer": response.content}

    return synthesizer


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_plan_execute_agent(model_name: str | None = None):
    """
    Build and return a compiled Plan-Execute StateGraph backed by Ollama.
    """
    model = model_name or OLLAMA_MODEL
    llm = ChatOllama(model=model, base_url=OLLAMA_BASE_URL, temperature=0)

    graph = StateGraph(PlanExecuteState)
    graph.add_node("planner",     _make_planner(llm))
    graph.add_node("executor",    _make_executor(llm, ALL_TOOLS))
    graph.add_node("synthesizer", _make_synthesizer(llm))

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_conditional_edges(
        "executor",
        _should_continue,
        path_map={"execute": "executor", "synthesize": "synthesizer"},
    )
    graph.add_edge("synthesizer", END)

    return graph.compile()


# ── Runner ────────────────────────────────────────────────────────────────────

def run_plan_execute_agent(
    question: str,
    model_name: str | None = None,
) -> dict[str, Any]:
    """
    Run the Plan-Execute agent on a single question and return structured results.

    Returns a dict compatible with AgentRunOut:
      {
        answer:        str    — synthesized final answer
        tool_calls:    list   — each tool invocation made during execution
        num_steps:     int    — number of plan steps executed
        latency_s:     float  — wall-clock time in seconds
        total_tokens:  int    — 0 (Ollama StateGraph doesn't surface per-message tokens easily)
        plan:          list[str]  — the decomposed step descriptions
        step_results:  list[str]  — each step's raw output
      }
    """
    agent = build_plan_execute_agent(model_name)

    t0 = time.perf_counter()
    result = agent.invoke({"input": question})
    latency_s = time.perf_counter() - t0

    plan         = result.get("plan", [])
    step_results = result.get("step_results", [])
    final_answer = result.get("final_answer", "")

    logger.info(
        "Plan-Execute agent completed: steps=%d latency=%.2fs",
        len(plan), latency_s,
    )

    # Represent each executed step as a "tool_call" entry for observability
    step_tool_calls = [
        {"name": f"step_{i + 1}", "args": {"description": plan[i]}, "id": f"step-{i}"}
        for i in range(len(plan))
    ]

    return {
        "answer":        final_answer,
        "tool_calls":    step_tool_calls,
        "num_steps":     len(plan),
        "latency_s":     round(latency_s, 3),
        "total_tokens":  0,
        "input_tokens":  0,
        "output_tokens": 0,
        "plan":          plan,
        "step_results":  step_results,
    }
