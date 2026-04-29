"""
LangSmith experiment tracking service.

All functions degrade gracefully when LANGCHAIN_API_KEY is not set — the
eval pipeline continues to work; LangSmith tracking is simply skipped.
"""
import os
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


def _langsmith_enabled() -> bool:
    return bool(os.getenv("LANGCHAIN_API_KEY"))


def ensure_dataset(
    name: str,
    samples: list[dict[str, Any]],
) -> str | None:
    """
    Upload samples to LangSmith as a named dataset.

    Each sample dict is expected to have at minimum:
      question (str), ground_truth (str)

    Returns the dataset name (used as identifier in log_experiment),
    or None if LangSmith is not configured.
    """
    if not _langsmith_enabled():
        logger.info("LangSmith not configured — skipping dataset upload.")
        return None

    try:
        from langsmith import Client

        client = Client()

        # Avoid duplicate datasets — check if it already exists
        existing = list(client.list_datasets(dataset_name=name))
        if existing:
            logger.info("LangSmith dataset '%s' already exists — reusing.", name)
            return name

        dataset = client.create_dataset(
            dataset_name=name,
            description=f"EvalForge dataset: {name}",
        )

        examples = []
        for s in samples:
            d = s.model_dump() if hasattr(s, "model_dump") else dict(s)
            examples.append(
                {
                    "inputs":  {"question": d.get("question") or d.get("user_input", "")},
                    "outputs": {"answer":   d.get("ground_truth") or d.get("reference", "")},
                }
            )
        client.create_examples(dataset_id=dataset.id, examples=examples)
        logger.info("Created LangSmith dataset '%s' with %d examples.", name, len(examples))
        return name

    except Exception as exc:
        logger.warning("LangSmith dataset creation failed: %s", exc)
        return None


def log_experiment(
    experiment_name: str,
    dataset_name: str,
    target_fn: Callable[[dict], dict],
    ragas_scores: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Log a completed evaluation run to LangSmith.

    Rather than re-running the pipeline inside LangSmith's evaluate(),
    we push the pre-computed RAGAS scores as feedback on a dummy experiment.
    This records the scores in the LangSmith UI without a second API call.

    Returns a dict with {experiment_name, url} or None if not configured.
    """
    if not _langsmith_enabled() or not dataset_name:
        logger.info("LangSmith not configured — skipping experiment logging.")
        return None

    try:
        from langsmith import Client
        from langsmith.evaluation import evaluate as ls_evaluate

        client = Client()

        # Build a simple pass-through target that echoes the question back.
        # We attach RAGAS scores as evaluator feedback, so the target output
        # itself doesn't matter — only the scores logged alongside it do.
        def _target(inputs: dict) -> dict:
            return target_fn(inputs)

        # Wrap each RAGAS metric as a LangSmith evaluator so scores show up
        # on individual runs inside the experiment UI.
        evaluators = _build_ragas_evaluators(ragas_scores)

        results = ls_evaluate(
            _target,
            data=dataset_name,
            evaluators=evaluators,
            experiment_prefix=experiment_name,
            metadata=metadata or {},
            max_concurrency=1,
        )

        return {
            "experiment_name": results.experiment_name,
            "url": getattr(results, "url", None),
        }

    except Exception as exc:
        logger.warning("LangSmith experiment logging failed: %s", exc)
        return None


def _build_ragas_evaluators(ragas_scores: dict[str, Any]) -> list[Callable]:
    """
    Create a LangSmith evaluator for each RAGAS metric that has a score.

    Each evaluator always returns the pre-computed score, regardless of the
    individual sample — this records the dataset-level mean in LangSmith.
    """
    evaluators = []
    for metric_name, score in ragas_scores.items():
        if score is None:
            continue

        # Capture metric_name and score in closure
        def _make_evaluator(key: str, val: float) -> Callable:
            def _evaluator(
                inputs: dict,
                outputs: dict,
                reference_outputs: dict | None = None,
            ) -> dict:
                return {"key": key, "score": val}
            _evaluator.__name__ = key
            return _evaluator

        evaluators.append(_make_evaluator(metric_name, score))

    return evaluators
