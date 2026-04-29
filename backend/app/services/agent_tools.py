"""
Shared tool definitions for EvalForge agents.

All tools here use mock/local implementations so no external API keys are needed.
In production, swap search_web with a real provider:
  - Tavily:   pip install tavily-python  →  TavilySearchResults from langchain_community
  - SerpAPI:  pip install google-search-results → SerpAPIWrapper
  - DuckDuckGo: pip install duckduckgo-search → DuckDuckGoSearchRun
"""
import math
from datetime import date
from langchain_core.tools import tool


@tool
def calculator(expression: str) -> str:
    """
    Evaluate a mathematical expression and return the result.

    Supports standard arithmetic: +, -, *, /, **, sqrt, abs, round.
    Examples: "25 * 48", "sqrt(144)", "2 ** 10", "(3 + 5) * 12"
    """
    # Sandboxed eval — only math builtins, no builtins like __import__
    safe_globals = {
        "__builtins__": {},
        "sqrt": math.sqrt,
        "abs": abs,
        "round": round,
        "pow": pow,
        "log": math.log,
        "log10": math.log10,
        "pi": math.pi,
        "e": math.e,
    }
    try:
        result = eval(expression.strip(), safe_globals)  # noqa: S307
        return str(result)
    except ZeroDivisionError:
        return "Error: division by zero"
    except Exception as exc:
        return f"Error evaluating '{expression}': {exc}"


@tool
def get_current_date() -> str:
    """
    Return today's date in ISO 8601 format (YYYY-MM-DD).

    Use this when the question involves today's date, current year,
    or any time-relative calculation.
    """
    return date.today().isoformat()


@tool
def search_web(query: str) -> str:
    """
    Search the web for up-to-date information about a topic.

    Use this for questions about current events, facts, people, places,
    or anything that requires external knowledge beyond your training data.

    NOTE: This is a mock implementation for local development.
    Swap with TavilySearchResults or DuckDuckGoSearchRun in production.
    """
    # Mock responses for common query patterns — realistic enough for demos
    query_lower = query.lower()

    if any(k in query_lower for k in ["capital", "capitals"]):
        return (
            "Search results: Paris is the capital of France. "
            "Berlin is the capital of Germany. "
            "Tokyo is the capital of Japan. "
            "Washington D.C. is the capital of the United States."
        )
    if any(k in query_lower for k in ["population", "largest city"]):
        return (
            "Search results: Tokyo has a population of ~13.9 million in the city proper. "
            "Mumbai has ~20 million. New York has ~8.3 million. "
            "Shanghai has ~24 million."
        )
    if any(k in query_lower for k in ["python", "programming"]):
        return (
            "Search results: Python is a high-level, interpreted programming language "
            "known for its readability. Created by Guido van Rossum in 1991. "
            "Latest stable version is Python 3.13."
        )
    if any(k in query_lower for k in ["llm", "language model", "gpt", "ai"]):
        return (
            "Search results: Large Language Models (LLMs) are AI systems trained on "
            "vast text corpora. Notable examples include GPT-4, Claude, Gemini, and "
            "open-source models like LLaMA and Mistral."
        )

    # Generic fallback
    return (
        f"Search results for '{query}': This topic relates to general knowledge. "
        "For accurate, up-to-date information, consult authoritative sources such as "
        "Wikipedia, official websites, or academic publications."
    )


# Convenience list — import this in agent builders
ALL_TOOLS = [calculator, get_current_date, search_web]
