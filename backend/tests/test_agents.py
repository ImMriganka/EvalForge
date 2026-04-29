"""
Phase 3 tests — agent tools unit tests + mocked /agents/run endpoint.

Ollama / LangGraph calls are mocked so tests are fast and offline.
"""
import pytest
from datetime import date
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.database import engine, Base
from app.services.agent_tools import calculator, get_current_date, search_web


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)

MOCK_AGENT_RESULT = {
    "answer":        "The answer is 1200.",
    "tool_calls":    [{"name": "calculator", "args": {"expression": "25 * 48"}, "id": "tc1"}],
    "num_steps":     1,
    "latency_s":     0.42,
    "total_tokens":  250,
    "input_tokens":  200,
    "output_tokens": 50,
    "plan":          [],
    "step_results":  [],
}

MOCK_PLAN_EXECUTE_RESULT = {
    "answer":        "Paris is the capital of France and Berlin is the capital of Germany.",
    "tool_calls":    [
        {"name": "step_1", "args": {"description": "Find capital of France"}, "id": "step-0"},
        {"name": "step_2", "args": {"description": "Find capital of Germany"}, "id": "step-1"},
    ],
    "num_steps":     2,
    "latency_s":     1.85,
    "total_tokens":  0,
    "input_tokens":  0,
    "output_tokens": 0,
    "plan":          ["Find capital of France", "Find capital of Germany"],
    "step_results":  ["Paris is the capital of France.", "Berlin is the capital of Germany."],
}


# ── Tool unit tests (no LLM needed) ──────────────────────────────────────────

class TestCalculatorTool:
    def test_basic_multiplication(self):
        result = calculator.invoke({"expression": "25 * 48"})
        assert result == "1200"

    def test_addition(self):
        result = calculator.invoke({"expression": "100 + 200"})
        assert result == "300"

    def test_exponentiation(self):
        result = calculator.invoke({"expression": "2 ** 10"})
        assert result == "1024"

    def test_sqrt(self):
        result = calculator.invoke({"expression": "sqrt(144)"})
        assert result == "12.0"

    def test_division_by_zero(self):
        result = calculator.invoke({"expression": "1 / 0"})
        assert "zero" in result.lower()

    def test_invalid_expression(self):
        result = calculator.invoke({"expression": "import os"})
        assert "error" in result.lower()

    def test_float_result(self):
        result = calculator.invoke({"expression": "10 / 3"})
        assert float(result) == pytest.approx(3.333, rel=0.01)


class TestGetCurrentDateTool:
    def test_returns_iso_format(self):
        result = get_current_date.invoke({})
        # Should parse as a valid date
        parsed = date.fromisoformat(result)
        assert parsed == date.today()

    def test_format_is_yyyy_mm_dd(self):
        result = get_current_date.invoke({})
        parts = result.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4   # year
        assert len(parts[1]) == 2   # month
        assert len(parts[2]) == 2   # day


class TestSearchWebTool:
    def test_capital_query_returns_paris(self):
        result = search_web.invoke({"query": "capital of France"})
        assert "Paris" in result

    def test_generic_query_returns_something(self):
        result = search_web.invoke({"query": "some random topic xyz"})
        assert isinstance(result, str)
        assert len(result) > 10

    def test_python_query(self):
        result = search_web.invoke({"query": "Python programming language"})
        assert "Python" in result


# ── /agents/run endpoint tests (mocked agents) ───────────────────────────────

class TestAgentsRunEndpoint:
    def test_react_agent_returns_valid_response(self):
        with patch("app.routers.agents.run_react_agent", return_value=MOCK_AGENT_RESULT):
            response = client.post(
                "/api/v1/agents/run",
                json={"question": "What is 25 * 48?", "agent_type": "react"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "The answer is 1200."
        assert data["num_steps"] == 1
        assert data["latency_s"] == pytest.approx(0.42)
        assert isinstance(data["tool_calls"], list)

    def test_plan_execute_returns_plan_and_steps(self):
        with patch(
            "app.routers.agents.run_plan_execute_agent",
            return_value=MOCK_PLAN_EXECUTE_RESULT,
        ):
            response = client.post(
                "/api/v1/agents/run",
                json={
                    "question": "What are the capitals of France and Germany?",
                    "agent_type": "plan_execute",
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert "Paris" in data["answer"]
        assert len(data["plan"]) == 2
        assert len(data["step_results"]) == 2
        assert data["num_steps"] == 2

    def test_unknown_agent_type_returns_422(self):
        response = client.post(
            "/api/v1/agents/run",
            json={"question": "test", "agent_type": "nonexistent"},
        )
        assert response.status_code == 422
        assert "nonexistent" in response.json()["detail"]

    def test_ollama_connection_error_returns_503(self):
        with patch(
            "app.routers.agents.run_react_agent",
            side_effect=ConnectionError("Connection refused"),
        ):
            response = client.post(
                "/api/v1/agents/run",
                json={"question": "test", "agent_type": "react"},
            )
        assert response.status_code == 503
        assert "ollama" in response.json()["detail"].lower()

    def test_generic_agent_error_returns_500(self):
        with patch(
            "app.routers.agents.run_react_agent",
            side_effect=RuntimeError("unexpected LangGraph error"),
        ):
            response = client.post(
                "/api/v1/agents/run",
                json={"question": "test", "agent_type": "react"},
            )
        assert response.status_code == 500

    def test_default_model_is_llama(self):
        """Verify the schema default model is llama3.1:8b (not an OpenAI model)."""
        captured = {}
        def capture_call(question, model_name=None):
            captured["model_name"] = model_name
            return MOCK_AGENT_RESULT

        with patch("app.routers.agents.run_react_agent", side_effect=capture_call):
            client.post(
                "/api/v1/agents/run",
                # no model_name → should use schema default
                json={"question": "test", "agent_type": "react"},
            )
        assert captured.get("model_name") == "llama3.1:8b"

    def test_response_has_all_fields(self):
        """AgentRunOut must include all expected fields."""
        with patch("app.routers.agents.run_react_agent", return_value=MOCK_AGENT_RESULT):
            response = client.post(
                "/api/v1/agents/run",
                json={"question": "test", "agent_type": "react"},
            )
        data = response.json()
        for field in ("answer", "tool_calls", "num_steps", "latency_s",
                      "total_tokens", "plan", "step_results"):
            assert field in data, f"Missing field: {field}"
