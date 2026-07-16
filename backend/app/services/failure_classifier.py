"""
Automatic failure classification for RAG queries.
"""

from typing import Optional

FAILURE_RECOMMENDATIONS = {
    "retrieval_miss": (
        "Retrieved chunks are semantically distant from the query. "
        "Consider: (1) re-embedding your corpus with a better model, "
        "(2) lowering similarity threshold, (3) increasing k."
    ),
    "retrieval_irrelevant": (
        "Retrieved chunks are on the wrong topic. "
        "Consider: (1) adding metadata filters, (2) hybrid BM25+vector retrieval, "
        "(3) query expansion or rewriting."
    ),
    "hallucination": (
        "LLM answer is not grounded in retrieved context despite relevant chunks. "
        "Consider: (1) stronger system prompt constraining the LLM to context only, "
        "(2) reducing LLM temperature, (3) using a more instruction-following model."
    ),
    "coverage_gap": (
        "Query asks about information not present in the vector database. "
        "Consider: (1) adding documentation about this topic, "
        "(2) implementing a 'I don't know' fallback when max similarity is below threshold."
    ),
    "chunking_issue": (
        "Answer information is split across chunk boundaries. "
        "Consider: (1) increasing chunk size, (2) using sentence-aware chunking, "
        "(3) adding chunk overlap."
    ),
    "none": "Query processed successfully with no detected failures.",
}


def classify_failure(
    faithfulness_score: Optional[float],
    context_precision_score: Optional[float],
    grounded_fraction: Optional[float],
    chunks: list[dict],
    query: str,
    answer: Optional[str],
    context_recall_score: Optional[float] = None,
) -> tuple[str, str, str]:
    """
    Classify the failure type for a query.

    Returns: (failure_type, explanation, recommendation)
    """
    if not chunks:
        return (
            "coverage_gap",
            "No chunks were retrieved for this query.",
            FAILURE_RECOMMENDATIONS["coverage_gap"],
        )

    # Check similarity scores
    sim_scores = [c.get("similarity_score") or 0 for c in chunks]
    avg_sim = sum(sim_scores) / len(sim_scores) if sim_scores else 0
    max_sim = max(sim_scores) if sim_scores else 0

    # Coverage gap: all chunks have very low similarity
    if max_sim < 0.3 and len(chunks) > 0:
        return (
            "coverage_gap",
            f"Maximum chunk similarity score was {max_sim:.2f}, indicating the query topic is not well-covered in the knowledge base.",
            FAILURE_RECOMMENDATIONS["coverage_gap"],
        )

    # Retrieval miss: low average similarity
    if avg_sim < 0.35 and max_sim < 0.5:
        return (
            "retrieval_miss",
            f"Retrieved chunks had low average similarity ({avg_sim:.2f}), suggesting the embedding model struggles with this query type.",
            FAILURE_RECOMMENDATIONS["retrieval_miss"],
        )

    # Context recall low: needed info not retrieved (spec v2)
    if context_recall_score is not None and context_recall_score < 0.4:
        return (
            "retrieval_miss",
            f"Context recall was {context_recall_score:.0%}, indicating retrieved chunks missed information needed to answer the query.",
            FAILURE_RECOMMENDATIONS["retrieval_miss"],
        )

    # Context precision low: wrong topic retrieved
    if context_precision_score is not None and context_precision_score < 0.3:
        return (
            "retrieval_irrelevant",
            f"Only {context_precision_score:.0%} of retrieved chunks were relevant to the answer, indicating topic mismatch.",
            FAILURE_RECOMMENDATIONS["retrieval_irrelevant"],
        )

    # Chunking issue: multiple low-relevance chunks needed for answer
    if len(chunks) >= 3:
        cited_chunks = [c for c in chunks if c.get("was_cited", False)]
        if len(cited_chunks) >= 3 and all(c.get("similarity_score", 0) < 0.6 for c in cited_chunks):
            return (
                "chunking_issue",
                "Answer required information from 3+ chunks with moderate similarity, suggesting content is fragmented across chunk boundaries.",
                FAILURE_RECOMMENDATIONS["chunking_issue"],
            )

    # Hallucination: low grounding despite relevant retrieval
    if grounded_fraction is not None and grounded_fraction < 0.5 and avg_sim > 0.5:
        return (
            "hallucination",
            f"Only {grounded_fraction:.0%} of answer sentences were grounded in retrieved context despite relevant chunks ({avg_sim:.2f} avg similarity).",
            FAILURE_RECOMMENDATIONS["hallucination"],
        )

    # Faithfulness low
    if faithfulness_score is not None and faithfulness_score < 0.5:
        return (
            "hallucination",
            f"Faithfulness score was {faithfulness_score:.2f}, indicating LLM generated content beyond what the context supports.",
            FAILURE_RECOMMENDATIONS["hallucination"],
        )

    return (
        "none",
        "No failure detected. Query processed successfully.",
        FAILURE_RECOMMENDATIONS["none"],
    )
