"""
RAGAS 0.2.x evaluation service.

Field mapping from EvalRequest.samples dicts → SingleTurnSample:
  question       → user_input
  contexts       → retrieved_contexts
  answer         → response
  ground_truth   → reference
"""
import os
from typing import Any

from ragas import evaluate
from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
from ragas.metrics import (
    Faithfulness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    FactualCorrectness,
    NoiseSensitivity,
)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


def build_ragas_dataset(samples: list) -> EvaluationDataset:
    """
    Translate EvalRequest samples (EvalSample objects or plain dicts) into
    a RAGAS EvaluationDataset.

    Accepted key names (both conventions supported):
      question / user_input
      contexts / retrieved_contexts   (list of strings)
      answer   / response
      ground_truth / reference
    """
    ragas_samples = []
    for s in samples:
        # Support both Pydantic model instances and plain dicts
        if hasattr(s, "model_dump"):
            d = s.model_dump()
        else:
            d = dict(s)

        ragas_samples.append(
            SingleTurnSample(
                user_input=d.get("user_input") or d.get("question"),
                retrieved_contexts=(
                    d.get("retrieved_contexts")
                    or d.get("contexts")
                    or []
                ),
                response=d.get("response") or d.get("answer"),
                reference=d.get("reference") or d.get("ground_truth"),
            )
        )
    return EvaluationDataset(samples=ragas_samples)


def run_rag_eval(
    samples: list[dict[str, Any]],
    model_name: str = "gpt-4o-mini",
) -> dict[str, float | None]:
    """
    Run RAGAS evaluation over the provided samples.

    Returns a dict of mean metric scores:
      {
        "faithfulness": 0.87,
        "answer_relevancy": 0.91,
        "context_precision": 0.78,
        "context_recall": 0.82,
        "factual_correctness": 0.75,
        "noise_sensitivity": 0.69,
      }
    Any metric that cannot be computed (e.g. missing fields) is returned as None.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY is not set. Cannot run RAGAS evaluation."
        )

    llm = LangchainLLMWrapper(ChatOpenAI(model=model_name, temperature=0))
    embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings())

    metrics = [
        Faithfulness(llm=llm),
        AnswerRelevancy(llm=llm, embeddings=embeddings),
        ContextPrecision(llm=llm),
        ContextRecall(llm=llm),
        FactualCorrectness(llm=llm),
        NoiseSensitivity(llm=llm),
    ]

    dataset = build_ragas_dataset(samples)

    result = evaluate(
        dataset,
        metrics=metrics,
        raise_exceptions=False,   # return NaN instead of crashing on bad samples
        show_progress=False,
        allow_nest_asyncio=True,  # required when called from inside FastAPI's event loop
    )

    scores_df = result.to_pandas()

    def _mean(col: str) -> float | None:
        if col not in scores_df.columns:
            return None
        series = scores_df[col].dropna()
        if series.empty:
            return None
        return round(float(series.mean()), 4)

    return {
        "faithfulness":       _mean("faithfulness"),
        "answer_relevancy":   _mean("answer_relevancy"),
        "context_precision":  _mean("context_precision"),
        "context_recall":     _mean("context_recall"),
        "factual_correctness": _mean("factual_correctness"),
        "noise_sensitivity":  _mean("noise_sensitivity"),
    }
