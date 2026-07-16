"""
RAGAS-inspired metrics computed using Hugging Face Inference API (free, deployable anywhere)
with Ollama fallback for local development.
Implements faithfulness, answer relevance, context precision, context recall.
"""

import json
from typing import Optional

import httpx
import numpy as np
import structlog

from app.services.ml_models import get_embedding_model

logger = structlog.get_logger()


def cosine_similarity(a: list, b: list) -> float:
    """Compute cosine similarity between two vectors."""
    a, b = np.array(a), np.array(b)
    norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


async def llm_generate(
    prompt: str,
    ollama_url: str,
    ollama_model: str,
    hf_token: Optional[str] = None,
    hf_model: str = "HuggingFaceH4/zephyr-7b-beta",
) -> Optional[str]:
    """
    Generate text using best available LLM provider:
    1. Hugging Face Inference API (free, deployable anywhere) — if HF_API_TOKEN is set
    2. Ollama (local) — fallback
    Returns None if both fail.
    """
    # Strategy 1: Hugging Face Inference API (free, works everywhere)
    if hf_token:
        try:
            api_url = f"https://api-inference.huggingface.co/models/{hf_model}"
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    api_url,
                    json={
                        "inputs": prompt,
                        "parameters": {
                            "max_new_tokens": 512,
                            "temperature": 0.3,
                            "do_sample": False,
                        },
                    },
                    headers={"Authorization": f"Bearer {hf_token}"},
                )
                if resp.status_code == 200:
                    result = resp.json()
                    # HF can return list of dicts or a single dict
                    if isinstance(result, list) and len(result) > 0:
                        return result[0].get("generated_text", "")
                    elif isinstance(result, dict):
                        return result.get("generated_text", "")
                elif resp.status_code == 503:
                    # Model is loading on HF servers, wait and retry once
                    logger.info("HF model is loading, waiting 10s...")
                    import asyncio

                    await asyncio.sleep(10)
                    resp = await client.post(
                        api_url,
                        json={
                            "inputs": prompt,
                            "parameters": {
                                "max_new_tokens": 512,
                                "temperature": 0.3,
                                "do_sample": False,
                            },
                        },
                        headers={"Authorization": f"Bearer {hf_token}"},
                    )
                    if resp.status_code == 200:
                        result = resp.json()
                        if isinstance(result, list) and len(result) > 0:
                            return result[0].get("generated_text", "")
                        elif isinstance(result, dict):
                            return result.get("generated_text", "")
                else:
                    logger.warning(
                        "HF API returned non-200", status=resp.status_code, body=resp.text[:200]
                    )
        except Exception as e:
            logger.warning("Hugging Face API call failed, falling back to Ollama", error=str(e))

    # Strategy 2: Ollama (local fallback)
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{ollama_url}/api/generate",
                json={"model": ollama_model, "prompt": prompt, "stream": False},
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
    except Exception as e:
        logger.warning("Ollama call also failed", error=str(e))

    return None


async def compute_faithfulness(
    answer: str,
    context_chunks: list[str],
    llm_url: str,
    llm_model: str,
    hf_token: Optional[str] = None,
    hf_model: str = "HuggingFaceH4/zephyr-7b-beta",
) -> float:
    """
    Faithfulness: What fraction of answer claims are supported by context?
    Uses LLM to extract claims, then checks each against context.
    """
    if not answer or not context_chunks:
        return 0.0

    context = "\n\n".join(context_chunks[:5])  # Use top 5 chunks

    # Extract claims from answer
    claim_prompt = f"""Extract all factual claims from this answer as a JSON array of strings.
Only include specific factual statements, not general statements.
Return ONLY valid JSON array, no explanation.

Answer: {answer[:1000]}

JSON array of claims:"""

    claims_text = await llm_generate(claim_prompt, llm_url, llm_model, hf_token, hf_model)

    claims = []
    if claims_text:
        try:
            # Try to parse JSON
            start = claims_text.find("[")
            end = claims_text.rfind("]") + 1
            if start >= 0 and end > start:
                claims = json.loads(claims_text[start:end])
        except Exception:
            # Fallback: split by newline
            claims = [
                line.strip("- ").strip()
                for line in claims_text.split("\n")
                if len(line.strip()) > 10
            ][:5]

    if not claims:
        # Fallback to embedding-based check
        model_obj = get_embedding_model()
        if not model_obj:
            return 0.5
        answer_emb = model_obj.encode(answer).tolist()
        context_emb = model_obj.encode(context).tolist()
        return round(cosine_similarity(answer_emb, context_emb), 3)

    # Check each claim against context
    supported = 0
    verify_prompt_template = """Does the following context support this claim? 
Answer only 'yes' or 'no'.

Context: {context}

Claim: {claim}

Answer (yes/no):"""

    for claim in claims[:5]:  # Limit to 5 claims for speed
        response = await llm_generate(
            verify_prompt_template.format(context=context[:2000], claim=claim),
            llm_url,
            llm_model,
            hf_token,
            hf_model,
        )
        if response and "yes" in response.lower()[:20]:
            supported += 1

    return round(supported / len(claims), 3) if claims else 0.5


async def compute_answer_relevance(
    query: str,
    answer: str,
    llm_url: str,
    llm_model: str,
    hf_token: Optional[str] = None,
    hf_model: str = "HuggingFaceH4/zephyr-7b-beta",
) -> float:
    """
    Answer Relevance: Does the answer address the question?
    Generate synthetic questions from the answer, measure similarity to original.
    """
    if not query or not answer:
        return 0.0

    model_obj = get_embedding_model()
    if not model_obj:
        return 0.5

    gen_prompt = f"""Generate 3 questions that this answer would be the response to.
Return ONLY the questions, one per line, no numbering.

Answer: {answer[:500]}

Questions:"""

    questions_text = await llm_generate(gen_prompt, llm_url, llm_model, hf_token, hf_model)

    if not questions_text:
        # Fallback: direct embedding similarity
        q_emb = model_obj.encode(query).tolist()
        a_emb = model_obj.encode(answer[:500]).tolist()
        return round(max(0, cosine_similarity(q_emb, a_emb)), 3)

    generated_questions = [
        q.strip() for q in questions_text.strip().split("\n") if len(q.strip()) > 5
    ][:3]

    if not generated_questions:
        q_emb = model_obj.encode(query).tolist()
        a_emb = model_obj.encode(answer[:500]).tolist()
        return round(max(0, cosine_similarity(q_emb, a_emb)), 3)

    query_emb = model_obj.encode(query).tolist()
    similarities = []
    for gq in generated_questions:
        gq_emb = model_obj.encode(gq).tolist()
        sim = cosine_similarity(query_emb, gq_emb)
        similarities.append(sim)

    return round(float(np.mean(similarities)), 3) if similarities else 0.5


def compute_context_precision(chunks: list[dict], was_grounded: bool) -> float:
    """
    Context Precision: What fraction of retrieved chunks contributed to the answer?
    Uses citation tracking from grounding results.
    """
    if not chunks:
        return 0.0
    cited = sum(1 for c in chunks if c.get("was_cited", False))
    return round(cited / len(chunks), 3)


async def compute_all_metrics(
    query: str,
    answer: str,
    context_chunks: list[dict],
    ollama_url: str,
    model: str,
    hf_token: Optional[str] = None,
    hf_model: str = "HuggingFaceH4/zephyr-7b-beta",
) -> dict:
    """Compute all RAGAS-inspired metrics using best available LLM provider."""
    chunk_texts = [c["chunk_text"] for c in context_chunks]

    try:
        faithfulness = await compute_faithfulness(
            answer, chunk_texts, ollama_url, model, hf_token, hf_model
        )
    except Exception as e:
        logger.warning("Faithfulness computation failed", error=str(e))
        faithfulness = None

    try:
        answer_relevance = await compute_answer_relevance(
            query, answer, ollama_url, model, hf_token, hf_model
        )
    except Exception as e:
        logger.warning("Answer relevance computation failed", error=str(e))
        answer_relevance = None

    context_precision = compute_context_precision(context_chunks, faithfulness is not None)

    context_recall = None
    try:
        from app.services.context_recall import compute_context_recall

        context_recall = await compute_context_recall(
            query,
            chunk_texts,
            answer,
            ollama_url=ollama_url,
            model=model,
            hf_token=hf_token,
            hf_model=hf_model,
            prefer_llm=bool(hf_token),
        )
    except Exception as e:
        logger.warning("Context recall computation failed", error=str(e))
        try:
            from app.services.context_recall import compute_context_recall_heuristic

            context_recall = compute_context_recall_heuristic(query, chunk_texts, answer)
        except Exception:
            context_recall = None

    return {
        "faithfulness_score": faithfulness,
        "answer_relevance_score": answer_relevance,
        "context_precision_score": context_precision,
        "context_recall_score": context_recall,
    }
