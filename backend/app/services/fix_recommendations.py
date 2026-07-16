"""
Automated Fix Recommendations (PRD v2.0 F8).
Clusters coverage gap queries by topic and surfaces actionable suggestions.
"""

import json
from typing import Optional

import numpy as np
import structlog

from app.services.ml_models import get_embedding_model

logger = structlog.get_logger()


def generate_fix_recommendations(
    coverage_gap_queries: list[dict],
    min_cluster_size: int = 3,
    min_samples: int = 1,
) -> list[dict]:
    """
    Cluster coverage_gap queries by topic using HDBSCAN on embeddings.

    Args:
        coverage_gap_queries: list of dicts with 'query_text' key
        min_cluster_size: minimum queries to form a cluster

    Returns:
        list of recommendation dicts:
        [{type, topic_description, affected_query_count, sample_queries}]
    """
    if len(coverage_gap_queries) < min_cluster_size:
        return []

    model = get_embedding_model()
    if not model:
        # Fallback: simple keyword grouping
        return _keyword_fallback_recommendations(coverage_gap_queries)

    try:
        # Encode all queries
        queries = [q["query_text"] for q in coverage_gap_queries]
        embeddings = model.encode(queries, show_progress_bar=False)

        # Try HDBSCAN clustering
        try:
            import hdbscan

            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=min_cluster_size,
                min_samples=min_samples,
                metric="euclidean",
                cluster_selection_epsilon=0.5,
            )
            cluster_labels = clusterer.fit_predict(embeddings)
        except ImportError:
            # Fallback: sklearn DBSCAN
            try:
                from sklearn.cluster import DBSCAN

                clusterer = DBSCAN(eps=0.5, min_samples=min_samples)
                cluster_labels = clusterer.fit_predict(embeddings)
            except ImportError:
                return _keyword_fallback_recommendations(coverage_gap_queries)

        # Group queries by cluster
        clusters: dict[int, list[dict]] = {}
        for i, label in enumerate(cluster_labels):
            if label == -1:  # Noise
                continue
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(coverage_gap_queries[i])

        recommendations = []
        for label, cluster_queries in clusters.items():
            if len(cluster_queries) < min_cluster_size:
                continue

            # Find centroid query (closest to cluster center)
            cluster_indices = [i for i, label_id in enumerate(cluster_labels) if label_id == label]
            cluster_embs = embeddings[cluster_indices]
            centroid = np.mean(cluster_embs, axis=0)
            centroid_distances = np.linalg.norm(cluster_embs - centroid, axis=1)
            centroid_idx = cluster_indices[int(np.argmin(centroid_distances))]

            sample_queries = [q["query_text"] for q in cluster_queries[:5]]
            topic = queries[centroid_idx]

            recommendations.append(
                {
                    "recommendation_type": "coverage_gap",
                    "topic_description": (
                        f"Add more documentation on '{topic[:100]}' — "
                        f"{len(cluster_queries)} queries had coverage gaps in this area"
                    ),
                    "affected_query_count": len(cluster_queries),
                    "sample_queries": json.dumps(sample_queries),
                }
            )

        # Sort by affected query count descending
        recommendations.sort(key=lambda r: r["affected_query_count"], reverse=True)
        return recommendations

    except Exception as e:
        logger.warning("Clustering failed, falling back to keyword grouping", error=str(e))
        return _keyword_fallback_recommendations(coverage_gap_queries)


def _keyword_fallback_recommendations(queries: list[dict]) -> list[dict]:
    """Simple keyword-based grouping fallback."""
    import re
    from collections import Counter

    # Extract top keywords excluding common stop words
    stop_words = {
        "what",
        "how",
        "why",
        "when",
        "where",
        "which",
        "who",
        "whom",
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "do",
        "does",
        "did",
        "can",
        "could",
        "will",
        "would",
        "should",
        "may",
        "might",
        "shall",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "this",
        "that",
        "these",
        "those",
        "am",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "having",
        "get",
        "got",
        "getting",
        "make",
        "made",
        "making",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "out",
        "off",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "here",
        "there",
        "and",
        "but",
        "or",
        "nor",
        "not",
        "so",
        "yet",
        "if",
        "because",
    }

    word_freq = Counter()
    for q in queries:
        words = re.findall(r"\b[a-zA-Z]{3,}\b", q["query_text"].lower())
        word_freq.update(w for w in words if w not in stop_words)

    if not word_freq:
        return []

    top_topics = word_freq.most_common(5)
    recommendations = []
    for topic, count in top_topics:
        related_queries = [q["query_text"] for q in queries if topic in q["query_text"].lower()][:5]
        if len(related_queries) >= 2:
            recommendations.append(
                {
                    "recommendation_type": "coverage_gap",
                    "topic_description": (
                        f"Add more documentation on '{topic}' — "
                        f"{count} queries had coverage gaps in this area"
                    ),
                    "affected_query_count": count,
                    "sample_queries": json.dumps(related_queries),
                }
            )

    return recommendations


def generate_retrieval_recommendation(
    bm25_better_ratio: float,
    total_queries: int,
) -> Optional[dict]:
    """Generate recommendation about BM25 vs vector search."""
    if total_queries < 10 or bm25_better_ratio < 0.3:
        return None

    return {
        "recommendation_type": "hybrid_search",
        "topic_description": (
            f"BM25 outperforms vector search on {bm25_better_ratio:.0%} of queries "
            f"({total_queries} total) — consider hybrid retrieval (BM25 + vector)"
        ),
        "affected_query_count": int(bm25_better_ratio * total_queries),
        "sample_queries": "[]",
    }


def generate_k_increase_recommendation(
    retrieval_miss_ratio: float,
    current_k: int = 3,
) -> Optional[dict]:
    """Generate recommendation about increasing k."""
    if retrieval_miss_ratio < 0.3:
        return None

    return {
        "recommendation_type": "chunking",
        "topic_description": (
            f"Consider increasing k from {current_k} to {current_k + 2} — "
            f"retrieval_miss accounts for {retrieval_miss_ratio:.0%} of failures for long-tail queries"
        ),
        "affected_query_count": int(retrieval_miss_ratio * 100),
        "sample_queries": "[]",
    }
