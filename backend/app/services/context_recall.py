"""
Context recall scoring for RAG traces.

Without labeled ground truth, RAGInspector uses a documented hybrid:

1. Heuristic (always available, default):
   - Query-term coverage (60%): fraction of significant query tokens that
     appear in retrieved context (case-insensitive substring match).
   - Answer-attribution coverage (40%, when answer present): fraction of
     answer sentences whose max cosine similarity to any chunk embedding
     is >= ATTRIBUTION_THRESHOLD. Approximates "needed answer content was
     present in retrieved context."

2. Optional LLM path (when HF/Ollama succeeds):
   - Extract atomic information needs from the query.
   - Ask whether each need is supported by the retrieved context.
   - Prefer LLM score when it returns a usable result; otherwise keep heuristic.

Score range: 0.0–1.0 (rounded to 3 decimals).
"""

from __future__ import annotations

import re
from typing import Optional

import structlog

logger = structlog.get_logger()

ATTRIBUTION_THRESHOLD = 0.35
_QUERY_WEIGHT = 0.6
_ANSWER_WEIGHT = 0.4

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "need",
        "what",
        "which",
        "who",
        "whom",
        "whose",
        "where",
        "when",
        "why",
        "how",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "as",
        "if",
        "than",
        "then",
        "so",
        "such",
        "into",
        "about",
        "over",
        "after",
        "before",
        "between",
        "under",
        "again",
        "further",
        "once",
        "here",
        "there",
        "all",
        "each",
        "few",
        "more",
        "most",
        "other",
        "some",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "too",
        "very",
        "just",
        "please",
        "tell",
        "me",
        "my",
        "your",
        "our",
        "their",
        "i",
        "you",
        "we",
        "they",
    }
)


def _significant_tokens(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9_-]{2,}", (text or "").lower())
    return [t for t in tokens if t not in _STOPWORDS]


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [s.strip() for s in parts if len(s.strip()) > 10]


def compute_context_recall_heuristic(
    query: str,
    context_chunks: list[str],
    answer: Optional[str] = None,
    *,
    attribution_threshold: float = ATTRIBUTION_THRESHOLD,
) -> float:
    """
    Heuristic context recall in [0, 1] without ground-truth labels.

    See module docstring for the formula.
    """
    chunks = [c for c in context_chunks if c and str(c).strip()]
    if not query or not chunks:
        return 0.0

    corpus = "\n".join(chunks).lower()
    terms = _significant_tokens(query)
    if terms:
        covered = sum(1 for t in terms if t in corpus)
        query_coverage = covered / len(terms)
    else:
        # No usable tokens — fall back to query↔context embedding similarity
        query_coverage = _max_query_chunk_similarity(query, chunks)

    answer_coverage: Optional[float] = None
    sentences = _split_sentences(answer or "")
    if sentences:
        answer_coverage = _answer_attribution_coverage(sentences, chunks, attribution_threshold)

    if answer_coverage is None:
        score = query_coverage
    else:
        score = _QUERY_WEIGHT * query_coverage + _ANSWER_WEIGHT * answer_coverage

    return round(max(0.0, min(1.0, float(score))), 3)


def _max_query_chunk_similarity(query: str, chunks: list[str]) -> float:
    try:
        from app.services.ragas_service import cosine_similarity, get_embedding_model

        model = get_embedding_model()
        if not model:
            return 0.5
        q_emb = model.encode(query).tolist()
        sims = [cosine_similarity(q_emb, model.encode(c[:1000]).tolist()) for c in chunks[:8]]
        return max(0.0, max(sims) if sims else 0.0)
    except Exception as e:
        logger.warning("query-chunk similarity fallback failed", error=str(e))
        return 0.5


def _answer_attribution_coverage(
    sentences: list[str],
    chunks: list[str],
    threshold: float,
) -> float:
    try:
        from app.services.ragas_service import cosine_similarity, get_embedding_model

        model = get_embedding_model()
        if not model:
            # Lexical fallback: sentence tokens present in corpus
            corpus = "\n".join(chunks).lower()
            hits = 0
            for s in sentences:
                terms = _significant_tokens(s)
                if not terms:
                    hits += 1
                    continue
                if sum(1 for t in terms if t in corpus) / len(terms) >= 0.4:
                    hits += 1
            return hits / len(sentences)

        chunk_embs = [model.encode(c[:1000]).tolist() for c in chunks[:8]]
        recalled = 0
        for s in sentences:
            s_emb = model.encode(s).tolist()
            best = max(cosine_similarity(s_emb, ce) for ce in chunk_embs)
            if best >= threshold:
                recalled += 1
        return recalled / len(sentences)
    except Exception as e:
        logger.warning("answer attribution coverage failed", error=str(e))
        corpus = "\n".join(chunks).lower()
        hits = sum(1 for s in sentences if any(t in corpus for t in _significant_tokens(s)[:5]))
        return hits / len(sentences) if sentences else 0.0


async def compute_context_recall_llm(
    query: str,
    context_chunks: list[str],
    llm_url: str,
    llm_model: str,
    hf_token: Optional[str] = None,
    hf_model: str = "HuggingFaceH4/zephyr-7b-beta",
) -> Optional[float]:
    """
    LLM path: extract information needs from the query and check each
    against retrieved context. Returns None if LLM unavailable/unusable.
    """
    if not query or not context_chunks:
        return 0.0

    from app.services.ragas_service import llm_generate

    context = "\n\n".join(context_chunks[:5])[:3000]
    extract_prompt = f"""List the distinct pieces of information needed to fully answer this question.
Return ONLY a JSON array of short strings (3-8 items). No explanation.

Question: {query[:800]}

JSON array:"""

    needs_text = await llm_generate(extract_prompt, llm_url, llm_model, hf_token, hf_model)
    needs: list[str] = []
    if needs_text:
        try:
            import json

            start = needs_text.find("[")
            end = needs_text.rfind("]") + 1
            if start >= 0 and end > start:
                parsed = json.loads(needs_text[start:end])
                if isinstance(parsed, list):
                    needs = [str(x).strip() for x in parsed if str(x).strip()][:8]
        except Exception:
            needs = [
                line.strip("- ").strip() for line in needs_text.split("\n") if len(line.strip()) > 8
            ][:5]

    if not needs:
        return None

    supported = 0
    verify_template = """Does the following context contain information about this need?
Answer only 'yes' or 'no'.

Context: {context}

Information need: {need}

Answer (yes/no):"""

    for need in needs:
        response = await llm_generate(
            verify_template.format(context=context, need=need),
            llm_url,
            llm_model,
            hf_token,
            hf_model,
        )
        if response and "yes" in response.lower()[:20]:
            supported += 1

    return round(supported / len(needs), 3)


async def compute_context_recall(
    query: str,
    context_chunks: list[str],
    answer: Optional[str] = None,
    *,
    ollama_url: Optional[str] = None,
    model: Optional[str] = None,
    hf_token: Optional[str] = None,
    hf_model: str = "HuggingFaceH4/zephyr-7b-beta",
    prefer_llm: bool = True,
) -> float:
    """
    Compute context recall: prefer LLM path when providers work, else heuristic.
    """
    heuristic = compute_context_recall_heuristic(query, context_chunks, answer)
    if not prefer_llm or not ollama_url or not model:
        return heuristic

    try:
        llm_score = await compute_context_recall_llm(
            query,
            context_chunks,
            ollama_url,
            model,
            hf_token,
            hf_model,
        )
        if llm_score is not None:
            return llm_score
    except Exception as e:
        logger.warning("LLM context recall failed; using heuristic", error=str(e))

    return heuristic
