"""
ReAct (Reason + Act) agent using LangGraph's create_react_agent.

The ReAct pattern loops:
  1. LLM reasons about the question
  2. LLM decides which tool to call (or answers directly)
  3. Tool result is fed back to the LLM
  4. Loop continues until the LLM produces a final answer (no tool call)

Architecture:
  User question
       │
       ▼
  [LLM: reason + decide]
       │
       ├─ tool call → [tool execution] ──┐
       │                                  │ (loop back)
       └─ final answer ◄──────────────────┘
"""
import os
import time
import logging
from typing import Any

from langchain_core.messages import AIMessage
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from app.services.agent_tools import ALL_TOOLS

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL",    "llama3.1:8b")

_SYSTEM_PROMPT = (
    "You are a helpful, precise assistant. "
    "Use the available tools when you need to perform calculations or look up information. "
    "Always think step-by-step before answering."
)


def build_react_agent(model_name: str | None = None):
    """
    Build and return a compiled ReAct agent backed by Ollama.

    The agent has access to: calculator, get_current_date, search_web.
    """
    model = model_name or OLLAMA_MODEL
    llm = ChatOllama(model=model, base_url=OLLAMA_BASE_URL, temperature=0)
    return create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        prompt=_SYSTEM_PROMPT,
    )


def run_react_agent(
    question: str,
    model_name: str | None = None,
) -> dict[str, Any]:
    """
    Run the ReAct agent on a single question and return structured results.

    Returns a dict compatible with AgentRunOut:
      {
        answer:        str    — the final answer
        tool_calls:    list   — each tool invocation: {name, args, id}
        num_steps:     int    — number of tool calls made
        latency_s:     float  — wall-clock time in seconds
        total_tokens:  int    — total tokens used across all LLM calls
        input_tokens:  int
        output_tokens: int
      }
    """
    agent = build_react_agent(model_name)

    t0 = time.perf_counter()
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]}
    )
    latency_s = time.perf_counter() - t0

    messages = result.get("messages", [])

    # Collect tool calls and token usage from every AIMessage in the run
    tool_calls: list[dict] = []
    total_input = total_output = total_tokens = 0

    for msg in messages:
        if isinstance(msg, AIMessage):
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append({
                        "name": tc.get("name", ""),
                        "args": tc.get("args", {}),
                        "id":   tc.get("id", ""),
                    })
            if msg.usage_metadata:
                total_input  += msg.usage_metadata.get("input_tokens", 0)
                total_output += msg.usage_metadata.get("output_tokens", 0)
                total_tokens += msg.usage_metadata.get("total_tokens", 0)

    # Final answer is always the last message's content
    final_msg = messages[-1] if messages else None
    answer = final_msg.content if final_msg else ""

    logger.info(
        "ReAct agent completed: steps=%d tokens=%d latency=%.2fs",
        len(tool_calls), total_tokens, latency_s,
    )

    return {
        "answer":        answer,
        "tool_calls":    tool_calls,
        "num_steps":     len(tool_calls),
        "latency_s":     round(latency_s, 3),
        "total_tokens":  total_tokens,
        "input_tokens":  total_input,
        "output_tokens": total_output,
        "plan":          [],
        "step_results":  [],
    }
