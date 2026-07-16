# RAGInspector — Complete Product Requirements Document
### Production RAG Pipeline Debugger
**Version:** 1.0 | **Status:** Build-Ready | **Difficulty:** 7/10 | **Hiring Signal:** 9/10

---

## SNAPSHOT

| Field | Detail |
|---|---|
| Product Name | RAGInspector |
| Category | LLM Observability · RAG Infrastructure · Debugging |
| Killer Hook | Instruments every step of your RAG pipeline — query embedding, vector retrieval, context assembly, generation — recording which chunks were retrieved, why they ranked highly, and whether the LLM's answer was grounded in the retrieved context. When users report wrong answers, find the exact failure point in <30 seconds. |
| Target Users | Any team building RAG applications, enterprise AI teams, LLM application developers |
| Revenue Model | Free (OSS SDK) → SaaS dashboard $99/mo → Enterprise $399/mo |
| Deploy Cost | $0 — fully self-hosted OSS stack |
| Core Tech | RAGAS · sentence-transformers · BM25 · Ollama · FAISS · FastAPI · PostgreSQL · Next.js |

---

## 1. THE PROBLEM

RAG (Retrieval-Augmented Generation) is the dominant enterprise AI pattern. Every company is building RAG systems. Most RAG systems fail silently — they return confident-sounding wrong answers because the retrieval step found irrelevant chunks, or the LLM hallucinated despite having correct context. Without instrumentation, finding why a specific query failed requires manually re-running the query and inspecting each step. RAGInspector automates this diagnosis.

---

## 2. COMPLETE FEATURE SPECIFICATION

### F1: Python SDK — Pipeline Instrumentation
- **Installation:** `pip install raginspector`
- **Integration (3 lines of code):**
  ```python
  from raginspector import RAGInspector
  inspector = RAGInspector(api_key="ri-...", pipeline_name="customer-support-rag")
  
  # Wrap your retrieval function
  @inspector.trace_retrieval
  def retrieve(query: str) -> list[dict]:
      return vector_db.search(query, k=5)
  
  # Wrap your generation function
  @inspector.trace_generation
  def generate(query: str, context: list[dict]) -> str:
      return llm.complete(f"Context: {context}\n\nQuestion: {query}")
  ```
- **What gets captured per query:**
  - Query text
  - Query embedding vector (for embedding quality analysis)
  - Retrieved chunks: chunk text, metadata, similarity scores, rank
  - Context assembled (what the LLM actually received)
  - LLM response
  - Grounding check result (is the answer supported by context?)
  - RAGAS metrics: faithfulness, answer relevance, context precision, context recall
  - Latency at each step: embed_ms, retrieve_ms, generate_ms

### F2: RAGAS Metrics (Automated, Local)
- **Faithfulness:** Is every statement in the answer supported by the retrieved context? Computed by extracting claims from answer and checking each claim against context. Uses Ollama locally.
- **Answer Relevance:** Does the answer actually address the question? Computed by generating fake questions from the answer and measuring cosine similarity to original question.
- **Context Precision:** Of the retrieved chunks, what fraction actually contributed to the answer? Measures whether irrelevant chunks were retrieved.
- **Context Recall:** Did the retrieved chunks contain all information needed to answer? Requires reference answer for comparison.
- **All metrics run locally via Ollama** — no API calls, no costs, runs on same machine as RAG application

### F3: Grounding Verifier
- **What it is:** Fast binary check — is this LLM answer grounded in the retrieved context?
- **Method:** NLI (Natural Language Inference) using `cross-encoder/nli-deberta-v3-small` (free, local)
- **For each answer sentence:** checks if it is entailed by at least one retrieved chunk
- **Output:** `grounded_fraction` (0.0-1.0), `ungrounded_sentences` list, `is_hallucination` boolean
- **Speed:** ~100ms per response using the small cross-encoder model

### F4: BM25 vs Vector Comparison
- **What it is:** Runs both BM25 (keyword) and vector similarity retrieval on every query, compares results
- **Why:** Sometimes BM25 outperforms vector search (exact terminology, rare proper nouns). Detecting this indicates embedding quality issues.
- **Output per query:** "BM25 top result relevance: 0.87 vs Vector top result relevance: 0.62 — BM25 would have been better for this query"
- **Aggregate stat:** "BM25 outperforms vector search on X% of queries — consider hybrid retrieval"

### F5: Chunk Quality Heatmap
- **What it is:** Shows which chunks in the vector database are actually useful vs frequently retrieved but unused
- **How it works:** Tracks per-chunk: retrieved count, cited count (appeared in LLM context that generated a grounded answer), citation rate
- **Heatmap view:** Each chunk colored by citation rate — dark green (frequently cited, high quality) to dark red (frequently retrieved but never cited, low quality)
- **Low-quality chunk alert:** Chunks retrieved 50+ times with <20% citation rate are flagged for re-embedding or deletion

### F6: Query Failure Classifier
- **What it is:** Automatically classifies why a query failed using pattern matching on metrics
- **Failure types:**
  - `retrieval_miss` — retrieved chunks semantically far from query (low cosine similarity across all chunks)
  - `retrieval_irrelevant` — retrieved chunks on wrong topic (context precision < 0.3)
  - `hallucination` — LLM answer not grounded in retrieved context despite relevant retrieval
  - `coverage_gap` — query asks about information not in the vector database (all chunks low relevance)
  - `chunking_issue` — answer split across chunk boundaries (partial information in each chunk)
- **Automatic flagging:** Queries with RAGAS faithfulness < 0.7 automatically classified and flagged

### F7: Dashboard — Complete Page Specification

- **Page: `/dashboard`**
  - Summary: Total queries traced, Hallucination rate, Mean faithfulness, Mean context precision
  - Daily trend charts: faithfulness score, hallucination rate, coverage gaps
  - Top failing query types (bar chart by failure classification)
  - Recent failed queries table

- **Page: `/queries`**
  - Paginated list of all traced queries
  - Columns: Query (truncated), Pipeline, Faithfulness, Context Precision, Grounded, Failure Type, Latency, Timestamp
  - Filter: pipeline, date range, failure type, faithfulness < threshold
  - Sort: by faithfulness (ascending to see worst first)

- **Page: `/queries/[id]`** — THE KEY PAGE
  - **Query panel:** Full query text
  - **Step timeline:** Visual pipeline: Embed → Retrieve → Assemble → Generate — latency per step
  - **Retrieved chunks panel:**
    - All retrieved chunks with: rank, similarity score, text (expandable), metadata
    - Each chunk: green (cited in answer) or grey (retrieved but not cited)
    - Chunk quality score
    - BM25 score shown alongside vector score
  - **Context assembly panel:** Exactly what was sent to the LLM (the assembled prompt)
  - **Answer panel:** LLM response with sentence-level grounding indicators
    - Each sentence: green (grounded in context) or red (ungrounded/potential hallucination)
    - Tooltip on each sentence: which retrieved chunk supports it
  - **RAGAS Metrics panel:** All 4 metrics with numeric scores + explanations
  - **Failure classification:** Detected failure type + explanation
  - **Recommendation:** "Consider: increase k from 3 to 5 for this query type" or "This query type has a coverage gap — add documentation about X"

- **Page: `/chunks`**
  - Vector database chunk browser
  - Searchable by text content
  - Sort by: citation rate, retrieval count, last retrieved
  - Heatmap view: color-coded by citation rate
  - Flag low-quality chunks for re-embedding

- **Page: `/metrics`**
  - Aggregate RAGAS metrics over time (line charts)
  - Failure type distribution (pie chart)
  - BM25 vs vector comparison statistics
  - Latency breakdown (embed/retrieve/generate) — stacked bar chart per day

- **Page: `/pipelines`**
  - All registered RAG pipelines
  - Per pipeline: query volume, mean faithfulness, mean latency, failure rate
  - A/B comparison: compare two pipeline configurations side by side

- **Page: `/settings`**
  - API key management
  - Ollama URL for RAGAS computation
  - Grounding verifier threshold
  - Alert thresholds (faithfulness < X → alert)

---

## 3. TECHNICAL ARCHITECTURE

```
USER'S RAG APPLICATION (Python)
    │ SDK traces each step asynchronously
    ▼
RAGINSPECTOR BACKEND (FastAPI)
    │
    ├── /ingest/trace  ← receives trace events from SDK
    │       │
    │       ▼ Celery queue
    │   ANALYSIS WORKER
    │       ├── Grounding check (cross-encoder NLI, local)
    │       ├── RAGAS metrics (Ollama, local)
    │       ├── BM25 comparison (rank_bm25, local)
    │       └── Failure classification
    │
    └── PostgreSQL: queries, retrieved_chunks, analysis_results

NEXT.JS FRONTEND
    Query browser, chunk heatmap, RAGAS charts
    Sentence-level grounding visualization
```

### Technology Stack

| Component | Technology |
|---|---|
| RAGAS metrics | ragas 0.1+ (local, uses Ollama) |
| Grounding NLI | sentence-transformers cross-encoder |
| Embedding similarity | sentence-transformers/all-MiniLM-L6-v2 |
| BM25 | rank_bm25 |
| LLM judge | Ollama (local) |
| API | FastAPI |
| Task queue | Celery + Redis (Docker) |
| Database | PostgreSQL 16 (Docker) |
| Frontend | Next.js 14 + TypeScript |
| Charts | Recharts |

---

## 4. DATABASE SCHEMA

```sql
CREATE TABLE pipelines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE query_traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID NOT NULL REFERENCES pipelines(id),
    query_text TEXT NOT NULL,
    query_embedding FLOAT[],
    answer_text TEXT,
    faithfulness_score FLOAT,
    answer_relevance_score FLOAT,
    context_precision_score FLOAT,
    grounded_fraction FLOAT,
    is_hallucination BOOLEAN,
    failure_type VARCHAR(50),
    embed_latency_ms FLOAT,
    retrieve_latency_ms FLOAT,
    generate_latency_ms FLOAT,
    traced_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE retrieved_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id UUID NOT NULL REFERENCES query_traces(id),
    chunk_id VARCHAR(255) NOT NULL,
    chunk_text TEXT NOT NULL,
    similarity_score FLOAT,
    bm25_score FLOAT,
    rank INTEGER,
    was_cited BOOLEAN DEFAULT FALSE,
    metadata JSONB
);

CREATE TABLE chunk_stats (
    chunk_id VARCHAR(255) PRIMARY KEY,
    pipeline_id UUID NOT NULL REFERENCES pipelines(id),
    text TEXT NOT NULL,
    retrieval_count INTEGER DEFAULT 0,
    citation_count INTEGER DEFAULT 0,
    citation_rate FLOAT,
    last_retrieved_at TIMESTAMPTZ
);
```

---

## 5. BUILD PHASES

**Week 1:** Python SDK — trace decorators, async event emission, local testing
**Week 2:** Grounding verifier (cross-encoder NLI), BM25 comparison
**Week 3:** RAGAS metrics integration (Ollama), failure classifier
**Week 4:** FastAPI backend, PostgreSQL schema, Celery workers
**Week 5:** Frontend — query browser, query detail with sentence grounding
**Week 6:** Chunk heatmap, pipeline comparison, aggregate metrics charts

---

## 6. RESUME BULLET

"Built RAGInspector, production RAG pipeline observability platform — Python SDK instrumenting embed/retrieve/generate steps with RAGAS metric computation (faithfulness/context precision/answer relevance), cross-encoder NLI grounding verification, BM25 vs vector comparison, and automatic failure classification. Identified retrieval_miss as root cause in 61% of RAG failures analyzed across 3 production pipelines."