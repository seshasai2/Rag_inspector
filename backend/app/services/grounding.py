"""
Grounding verifier using cross-encoder NLI to check if LLM answer
sentences are supported by retrieved chunks.
"""

import re
from typing import Optional

import structlog

from app.services.ml_models import get_nli_cross_encoder

logger = structlog.get_logger()


def get_cross_encoder():
    """Lazy NLI model — delegated to shared process cache."""
    return get_nli_cross_encoder()


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 10]


def check_grounding(
    answer_text: str,
    retrieved_chunks: list[dict],
    threshold: float = 0.5,
) -> dict:
    """
    Check if each sentence in the answer is grounded in retrieved chunks.

    Returns:
        {
            grounded_fraction: float,
            is_hallucination: bool,
            sentence_results: list[{sentence, is_grounded, supporting_chunk_id, confidence}]
        }
    """
    if not answer_text or not retrieved_chunks:
        return {
            "grounded_fraction": 0.0,
            "is_hallucination": True,
            "sentence_results": [],
        }

    model = get_cross_encoder()
    sentences = split_into_sentences(answer_text)

    if not sentences:
        return {
            "grounded_fraction": 1.0,
            "is_hallucination": False,
            "sentence_results": [],
        }

    sentence_results = []

    for i, sentence in enumerate(sentences):
        best_score = 0.0
        best_chunk_id = None

        if model:
            # Build pairs: (sentence, chunk_text) for NLI
            pairs = [(sentence, c["chunk_text"]) for c in retrieved_chunks]
            try:
                scores = model.predict(pairs, apply_softmax=True)
                # NLI labels: contradiction=0, neutral=1, entailment=2
                for j, score_arr in enumerate(scores):
                    entailment_score = float(score_arr[2])
                    if entailment_score > best_score:
                        best_score = entailment_score
                        best_chunk_id = retrieved_chunks[j].get("chunk_id")
            except Exception as e:
                logger.warning("NLI inference failed", error=str(e))
                # Fallback: keyword overlap
                best_score, best_chunk_id = _keyword_fallback(sentence, retrieved_chunks)
        else:
            best_score, best_chunk_id = _keyword_fallback(sentence, retrieved_chunks)

        is_grounded = best_score >= threshold
        sentence_results.append(
            {
                "sentence_text": sentence,
                "sentence_index": i,
                "is_grounded": is_grounded,
                "supporting_chunk_id": best_chunk_id if is_grounded else None,
                "confidence_score": round(best_score, 3),
            }
        )

    grounded_count = sum(1 for r in sentence_results if r["is_grounded"])
    grounded_fraction = grounded_count / len(sentence_results) if sentence_results else 0.0

    return {
        "grounded_fraction": round(grounded_fraction, 3),
        "is_hallucination": grounded_fraction < 0.5,
        "sentence_results": sentence_results,
    }


def _keyword_fallback(sentence: str, chunks: list[dict]) -> tuple[float, Optional[str]]:
    """Simple keyword overlap fallback when NLI model is unavailable."""
    sentence_words = set(sentence.lower().split())
    best_score = 0.0
    best_chunk_id = None

    for chunk in chunks:
        chunk_words = set(chunk["chunk_text"].lower().split())
        if not sentence_words:
            continue
        overlap = len(sentence_words & chunk_words) / len(sentence_words)
        if overlap > best_score:
            best_score = overlap
            best_chunk_id = chunk.get("chunk_id")

    return best_score, best_chunk_id
