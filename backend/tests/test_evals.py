"""
Phase 2 tests — eval_service unit tests + mocked /evals/run endpoint.

RAGAS and OpenAI calls are mocked so tests run without API keys.
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.database import engine, Base
from app.services.eval_service import (
    compute_trustworthiness,
    grade,
    build_results_payload,
)
from app.services.ragas_service import build_ragas_dataset


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)

SAMPLE_PAYLOAD = {
    "experiment_name": "test-run",
    "model_name": "gpt-4o-mini",
    "agent_type": "rag",
    "run_injection": False,
    "samples": [
        {
            "question": "What is the capital of France?",
            "contexts": ["Paris is the capital and most populous city of France."],
            "answer": "The capital of France is Paris.",
            "ground_truth": "Paris",
        }
    ],
}

MOCK_RAGAS_SCORES = {
    "faithfulness": 0.90,
    "answer_relevancy": 0.88,
    "context_precision": 0.82,
    "context_recall": 0.85,
    "factual_correctness": 0.80,
    "noise_sensitivity": 0.75,
}


# ── eval_service unit tests ───────────────────────────────────────────────────

class TestComputeTrustworthiness:
    def test_all_components_present(self):
        scores = {"faithfulness": 1.0, "factual_correctness": 1.0}
        injection = {"injection_rate": 0.0}
        result = compute_trustworthiness(scores, injection)
        # 0.50*1.0 + 0.20*1.0 + 0.30*(1-0.0) = 1.0
        assert result == 1.0

    def test_partial_injection(self):
        scores = {"faithfulness": 1.0, "factual_correctness": 1.0}
        injection = {"injection_rate": 0.5}
        result = compute_trustworthiness(scores, injection)
        # 0.50*1.0 + 0.20*1.0 + 0.30*0.5 = 0.85
        assert result == 0.85

    def test_no_injection_summary_defaults_to_full_robustness(self):
        scores = {"faithfulness": 0.80, "factual_correctness": 0.60}
        result = compute_trustworthiness(scores, None)
        # 0.50*0.80 + 0.20*0.60 + 0.30*1.0 = 0.40 + 0.12 + 0.30 = 0.82
        assert result == 0.82

    def test_missing_ragas_scores_default_to_zero(self):
        result = compute_trustworthiness({}, None)
        # 0 + 0 + 0.30 = 0.30
        assert result == 0.30


class TestGrade:
    def test_grade_a(self):
        assert grade(0.85) == "A — Production Ready"
        assert grade(1.0)  == "A — Production Ready"

    def test_grade_b(self):
        assert grade(0.70) == "B — Needs Monitoring"
        assert grade(0.84) == "B — Needs Monitoring"

    def test_grade_c(self):
        assert grade(0.55) == "C — Needs Work"
        assert grade(0.69) == "C — Needs Work"

    def test_grade_d(self):
        assert grade(0.0)  == "D — Not Production Safe"
        assert grade(0.54) == "D — Not Production Safe"


# ── ragas_service unit tests ──────────────────────────────────────────────────

class TestBuildRagasDataset:
    def test_maps_question_keys(self):
        samples = [
            {
                "question": "What is X?",
                "contexts": ["X is a thing."],
                "answer": "X is a thing.",
                "ground_truth": "X",
            }
        ]
        dataset = build_ragas_dataset(samples)
        assert len(dataset.samples) == 1
        s = dataset.samples[0]
        assert s.user_input == "What is X?"
        assert s.retrieved_contexts == ["X is a thing."]
        assert s.response == "X is a thing."
        assert s.reference == "X"

    def test_maps_user_input_keys(self):
        samples = [
            {
                "user_input": "What is Y?",
                "retrieved_contexts": ["Y is another thing."],
                "response": "Y is another thing.",
                "reference": "Y",
            }
        ]
        dataset = build_ragas_dataset(samples)
        s = dataset.samples[0]
        assert s.user_input == "What is Y?"
        assert s.reference == "Y"

    def test_empty_contexts_default(self):
        samples = [{"question": "Q?", "answer": "A", "ground_truth": "A"}]
        dataset = build_ragas_dataset(samples)
        assert dataset.samples[0].retrieved_contexts == []


# ── /evals/run endpoint test (mocked RAGAS) ──────────────────────────────────

class TestEvalsRunEndpoint:
    def test_run_eval_returns_trustworthiness(self):
        with (
            patch(
                "app.routers.evals.run_rag_eval",
                return_value=MOCK_RAGAS_SCORES,
            ),
            patch(
                "app.routers.evals.ensure_dataset",
                return_value=None,
            ),
            patch(
                "app.routers.evals.log_experiment",
                return_value=None,
            ),
        ):
            response = client.post("/api/v1/evals/run", json=SAMPLE_PAYLOAD)

        assert response.status_code == 200
        data = response.json()
        assert "experiment_id" in data
        assert data["experiment_id"] > 0

        results = data["results"]
        assert "ragas" in results
        assert "trustworthiness" in results
        assert "grade" in results
        assert 0.0 <= results["trustworthiness"] <= 1.0

    def test_run_eval_ragas_error_returns_500(self):
        with patch(
            "app.routers.evals.run_rag_eval",
            side_effect=RuntimeError("RAGAS internal error"),
        ):
            response = client.post("/api/v1/evals/run", json=SAMPLE_PAYLOAD)

        assert response.status_code == 500

    def test_run_eval_missing_api_key_returns_422(self):
        with patch(
            "app.routers.evals.run_rag_eval",
            side_effect=EnvironmentError("OPENAI_API_KEY is not set"),
        ):
            response = client.post("/api/v1/evals/run", json=SAMPLE_PAYLOAD)

        assert response.status_code == 422

    def test_experiment_persisted_in_db(self):
        with (
            patch("app.routers.evals.run_rag_eval", return_value=MOCK_RAGAS_SCORES),
            patch("app.routers.evals.ensure_dataset", return_value=None),
            patch("app.routers.evals.log_experiment", return_value=None),
        ):
            response = client.post("/api/v1/evals/run", json=SAMPLE_PAYLOAD)

        exp_id = response.json()["experiment_id"]

        # Fetch via experiments endpoint
        get_response = client.get(f"/api/v1/experiments/{exp_id}")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "test-run"
        assert get_response.json()["model_name"] == "gpt-4o-mini"
