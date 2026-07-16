# RAGInspector — Enterprise AI Knowledge Reliability Platform
## Agent-Executable Build Specification v3.0 — FINAL

**Classification:** Enterprise SaaS | AI Quality Engineering Platform  
**Positioning:** Enterprise AI Knowledge Reliability Platform — not RAG observability  
**Stack:** FastAPI · Next.js 14 · PostgreSQL · Redis · Celery · sentence-transformers · Ollama · Groq · Razorpay  
**GPU Requirement:** GTX 1650+ for Ollama Phi-3 Mini Q4 (LLM-as-judge). CPU handles NLI grounding.  
**Target Buyer:** VP Engineering / Head of AI / CTO at companies running RAG in production  
**Core Value:** We don't just tell you what's wrong with your RAG system. We fix it.

---

## AGENT INSTRUCTIONS

Build in exact sequence defined in BUILD ORDER (Section 17). Zero ambiguity tolerance.

**Non-negotiable invariants:**
- Trust Score (0–100) and Hallucination Cost ($/month) are hero metrics — every page references them
- Sentence-level grounding attribution is the core differentiator — never omit it
- Every recommendation has a Priority, Estimated Trust Improvement %, Estimated Cost, and Estimated Time
- All plans gate via `plan` field on the user record — check before every pro/enterprise route
- Razorpay is the payment processor — no Stripe, no PayPal
- Dark theme only across all UI — `#0D0F14` background, `#00D4FF` primary accent
- SDK must work with zero code changes for LangChain, LlamaIndex, Haystack

---

## 1. PRODUCT OVERVIEW

### 1.1 What RAGInspector Is

RAGInspector is an AI Quality Engineering platform that instruments every step of a RAG pipeline — query embedding, vector retrieval, context assembly, LLM generation — and then does five things no competitor does together:

1. **Measures** quality with RAGAS metrics + NLI sentence-level grounding
2. **Classifies** every failure by root cause: `retrieval_miss`, `context_miss`, `hallucination`
3. **Identifies** missing knowledge gaps that cause repeated failures
4. **Generates** fixes: document drafts, chunk removal recommendations, embedding model suggestions
5. **Verifies** that applied fixes actually improved Trust Score

The complete loop: **Detect → Explain → Recommend → Fix → Verify**

### 1.2 Hero Metrics

| Metric | Description | Where Displayed |
|---|---|---|
| **Trust Score** | Composite 0–100 from faithfulness, grounding, precision, reliability | Every page header |
| **Hallucination Cost** | Monthly USD estimated business impact | Dashboard, Executive view |
| **Knowledge Coverage %** | % of query topic surface covered by indexed knowledge | Knowledge Map page |
| **AI Quality Trend** | Trust Score trajectory over 30/90 days | Executive Dashboard |

### 1.3 Target Personas

| Persona | Pain | What They See |
|---|---|---|
| **AI Engineer** | Debugging RAG failures takes hours | Trace detail with sentence-level grounding + failure root cause |
| **ML Engineer** | No visibility into which chunks are stale | Chunk Studio + Retrieval Benchmark |
| **VP Engineering** | Cannot quantify RAG quality to stakeholders | Executive Dashboard: Trust Score, Hallucination Cost, Customer Impact |
| **CTO / Head of AI** | Cannot tell if RAG got better after changes | Auto Regression Detection + Quality Trend |

---

## 2. COMPLETE PROJECT STRUCTURE

```
raginspector/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py                      # Settings from env
│   │   ├── database.py                    # Async SQLAlchemy engine
│   │   ├── dependencies.py                # Auth + plan gate deps
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── auth.py                # Register, login, JWT, API key
│   │   │       ├── traces.py              # Ingest + query trace CRUD
│   │   │       ├── pipelines.py           # Pipeline CRUD + config
│   │   │       ├── metrics.py             # Dashboard + trend metrics
│   │   │       ├── failures.py            # Failure summary + patterns
│   │   │       ├── knowledge.py           # Gaps + coverage map + freshness
│   │   │       ├── autofix.py             # Recommendations + apply
│   │   │       ├── documents.py           # Doc management + freshness alerts
│   │   │       ├── benchmark.py           # Retrieval benchmark + LLM comparison
│   │   │       ├── simulator.py           # Retrieval simulator (what-if)
│   │   │       ├── prompts.py             # Prompt quality analyzer
│   │   │       ├── monitoring.py          # Continuous monitoring config + probes
│   │   │       ├── executive.py           # Executive dashboard data
│   │   │       ├── integrations.py        # Cross-project integration hooks
│   │   │       ├── reports.py             # PDF/Confluence/Notion export
│   │   │       └── billing.py             # Razorpay subscription management
│   │   ├── workers/
│   │   │   ├── ragas_worker.py            # Async RAGAS + grounding computation
│   │   │   ├── grounding_worker.py        # NLI grounding (CPU)
│   │   │   ├── knowledge_worker.py        # Gap detection + coverage update
│   │   │   ├── monitoring_worker.py       # Scheduled probe runner
│   │   │   ├── regression_worker.py       # Pre-deploy regression check
│   │   │   ├── freshness_worker.py        # Document stale detection
│   │   │   └── benchmark_worker.py        # Retrieval benchmark runner
│   │   ├── services/
│   │   │   ├── grounding.py               # NLI grounding service
│   │   │   ├── trust_scorer.py            # Trust Score computation
│   │   │   ├── failure_classifier.py      # Failure root cause classifier
│   │   │   ├── hallucination_cost.py      # Monthly cost estimator
│   │   │   ├── knowledge_gap.py           # Gap detection + clustering
│   │   │   ├── coverage_map.py            # Knowledge coverage computation
│   │   │   ├── chunk_optimizer.py         # Chunk size optimization
│   │   │   ├── retrieval_simulator.py     # What-if simulation engine
│   │   │   ├── prompt_analyzer.py         # Prompt quality scoring
│   │   │   ├── citation_scorer.py         # Citation quality scoring
│   │   │   ├── doc_generator.py           # AI doc draft generation
│   │   │   ├── knowledge_graph.py         # Document relationship graph
│   │   │   ├── ai_investigator.py         # Natural language query over metrics
│   │   │   ├── fix_planner.py             # Fix priority + effort estimator
│   │   │   ├── bm25_service.py            # BM25 retrieval
│   │   │   └── regression_detector.py     # Pre-deploy regression
│   │   └── models/                        # SQLAlchemy ORM models
│   │       ├── user.py
│   │       ├── pipeline.py
│   │       ├── trace.py
│   │       ├── chunk.py
│   │       ├── knowledge.py
│   │       ├── document.py
│   │       ├── benchmark.py
│   │       ├── monitoring.py
│   │       └── integration.py
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   └── requirements.txt
├── sdk/
│   ├── raginspector/
│   │   ├── __init__.py
│   │   ├── tracer.py                      # Core tracing decorators
│   │   ├── async_tracer.py                # Async version
│   │   ├── integrations/
│   │   │   ├── langchain.py               # LangChain callback handler
│   │   │   ├── llamaindex.py              # LlamaIndex event handler
│   │   │   └── haystack.py                # Haystack component wrapper
│   │   ├── client.py                      # HTTP client with batching
│   │   └── decorators.py                  # trace_rag() all-in-one decorator
│   ├── setup.py
│   └── README.md
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx                 # Root layout, dark theme
│   │   │   ├── page.tsx                   # Landing / redirect
│   │   │   ├── (auth)/
│   │   │   │   ├── login/page.tsx
│   │   │   │   └── register/page.tsx
│   │   │   ├── (app)/
│   │   │   │   ├── layout.tsx             # Sidebar + nav
│   │   │   │   ├── dashboard/page.tsx     # Main engineering dashboard
│   │   │   │   ├── executive/page.tsx     # Executive-only view
│   │   │   │   ├── traces/
│   │   │   │   │   ├── page.tsx           # Trace list with filters
│   │   │   │   │   └── [id]/page.tsx      # Sentence-level grounding view
│   │   │   │   ├── failures/page.tsx      # Failure analysis + patterns
│   │   │   │   ├── knowledge/
│   │   │   │   │   ├── map/page.tsx       # Knowledge coverage map
│   │   │   │   │   ├── gaps/page.tsx      # Gap list + drafts
│   │   │   │   │   ├── freshness/page.tsx # Document age + stale alerts
│   │   │   │   │   └── graph/page.tsx     # Knowledge graph visualization
│   │   │   │   ├── autofix/page.tsx       # Fix recommendations
│   │   │   │   ├── benchmark/
│   │   │   │   │   ├── retrieval/page.tsx # Retrieval strategy comparison
│   │   │   │   │   └── models/page.tsx    # Multi-LLM comparison
│   │   │   │   ├── studio/
│   │   │   │   │   ├── chunks/page.tsx    # Chunk Optimization Studio
│   │   │   │   │   ├── simulator/page.tsx # Retrieval Simulator
│   │   │   │   │   └── prompts/page.tsx   # Prompt Quality Analyzer
│   │   │   │   ├── monitoring/page.tsx    # Continuous monitoring config
│   │   │   │   ├── investigator/page.tsx  # AI Investigator chat
│   │   │   │   ├── reports/page.tsx       # PDF + integration exports
│   │   │   │   └── settings/
│   │   │   │       ├── pipeline/page.tsx
│   │   │   │       └── billing/page.tsx
│   │   ├── components/
│   │   │   ├── ui/                        # shadcn base
│   │   │   ├── trust-score-gauge.tsx
│   │   │   ├── hallucination-cost-card.tsx
│   │   │   ├── grounding-viewer.tsx       # Sentence-level color-coded view
│   │   │   ├── knowledge-coverage-bar.tsx
│   │   │   ├── failure-pie-chart.tsx
│   │   │   ├── trend-chart.tsx
│   │   │   ├── chunk-heatmap.tsx
│   │   │   ├── knowledge-graph-canvas.tsx
│   │   │   └── fix-planner-card.tsx
│   │   └── lib/
│   │       ├── api.ts                     # Typed API client
│   │       ├── auth.ts
│   │       └── constants.ts
│   ├── package.json
│   └── tailwind.config.ts
├── docker-compose.yml
├── docker-compose.prod.yml
└── .env.example
```

---

## 3. DATABASE SCHEMA (Complete — 16 Tables)

### 3.1 users
```sql
CREATE TABLE users (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                   VARCHAR(255) UNIQUE NOT NULL,
    hashed_password         VARCHAR(255) NOT NULL,
    full_name               VARCHAR(255),
    plan                    VARCHAR(50) DEFAULT 'free'
                            CHECK (plan IN ('free', 'pro', 'enterprise')),
    api_key                 VARCHAR(255) UNIQUE,
    razorpay_customer_id    VARCHAR(255),
    razorpay_subscription_id VARCHAR(255),
    plan_expires_at         TIMESTAMPTZ,
    is_active               BOOLEAN DEFAULT true,
    is_verified             BOOLEAN DEFAULT false,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_users_api_key ON users(api_key);
```

### 3.2 pipelines
```sql
CREATE TABLE pipelines (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID REFERENCES users(id) ON DELETE CASCADE,
    name                    VARCHAR(255) NOT NULL,
    framework               VARCHAR(100)
                            CHECK (framework IN ('langchain', 'llamaindex', 'haystack', 'custom')),
    description             TEXT,
    environment             VARCHAR(50) DEFAULT 'production'
                            CHECK (environment IN ('development', 'staging', 'production')),
    -- Business context for cost calculation
    queries_per_month       INTEGER DEFAULT 10000,
    cost_per_wrong_answer_usd FLOAT DEFAULT 5.0,
    -- Embedding model info
    embedding_model         VARCHAR(255) DEFAULT 'text-embedding-3-small',
    embedding_dimension     INTEGER DEFAULT 1536,
    chunk_size              INTEGER DEFAULT 512,
    chunk_overlap           INTEGER DEFAULT 50,
    top_k                   INTEGER DEFAULT 5,
    retrieval_strategy      VARCHAR(100) DEFAULT 'dense'
                            CHECK (retrieval_strategy IN ('dense', 'bm25', 'hybrid', 'colbert', 'splade')),
    -- Aggregated metrics (updated by workers)
    trust_score             FLOAT,
    total_traces            INTEGER DEFAULT 0,
    hallucination_rate      FLOAT DEFAULT 0.0,
    faithfulness_avg        FLOAT,
    context_precision_avg   FLOAT,
    context_recall_avg      FLOAT,
    answer_relevance_avg    FLOAT,
    knowledge_coverage_pct  FLOAT DEFAULT 0.0,
    -- State
    is_active               BOOLEAN DEFAULT true,
    baseline_trust_score    FLOAT,             -- set at first 100 traces
    last_regression_check   TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    last_trace_at           TIMESTAMPTZ,
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_pipelines_user ON pipelines(user_id, is_active);
```

### 3.3 query_traces
```sql
CREATE TABLE query_traces (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id             UUID REFERENCES pipelines(id) ON DELETE CASCADE,
    session_id              VARCHAR(255),                  -- group related queries
    -- Query
    query_text              TEXT NOT NULL,
    query_embedding         FLOAT[],
    -- Retrieved chunks
    retrieved_chunks        JSONB NOT NULL,
    -- list of {chunk_id, text, score, rank, source_doc_id}
    n_chunks_retrieved      INTEGER,
    -- Generation
    generated_answer        TEXT NOT NULL,
    llm_model               VARCHAR(255),
    llm_temperature         FLOAT,
    -- RAGAS metrics
    faithfulness            FLOAT,
    context_precision       FLOAT,
    context_recall          FLOAT,
    answer_relevance        FLOAT,
    -- Grounding (NLI)
    grounding_results       JSONB,
    -- list of {sentence, is_grounded, supporting_chunk_id, confidence, evidence_text}
    grounded_sentence_count INTEGER,
    total_sentence_count    INTEGER,
    grounding_rate          FLOAT,
    -- Citation quality
    citation_completeness   FLOAT,                         -- fraction of answer claims cited
    citation_relevance      FLOAT,
    citation_contradictions INTEGER DEFAULT 0,
    citation_unsupported    INTEGER DEFAULT 0,
    -- Prompt quality
    prompt_ambiguity_score  FLOAT,
    prompt_issues           JSONB,                         -- list of {type, description, fix}
    -- Classification
    failure_type            VARCHAR(100)
                            CHECK (failure_type IN
                            ('retrieval_miss', 'context_miss', 'hallucination', 'none')),
    failure_reason          TEXT,
    failure_confidence      FLOAT,
    -- Timing
    total_latency_ms        FLOAT,
    retrieval_latency_ms    FLOAT,
    generation_latency_ms   FLOAT,
    -- Cost tracking
    estimated_token_cost_usd FLOAT,
    -- Analysis state
    analysis_status         VARCHAR(50) DEFAULT 'pending'
                            CHECK (analysis_status IN
                            ('pending', 'analyzing', 'complete', 'failed')),
    created_at              TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_traces_pipeline_date ON query_traces(pipeline_id, created_at DESC);
CREATE INDEX idx_traces_failure ON query_traces(pipeline_id, failure_type);
CREATE INDEX idx_traces_status ON query_traces(analysis_status);
CREATE INDEX idx_traces_session ON query_traces(pipeline_id, session_id);
```

### 3.4 chunk_stats
```sql
CREATE TABLE chunk_stats (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id             UUID REFERENCES pipelines(id) ON DELETE CASCADE,
    chunk_id                VARCHAR(500) NOT NULL,
    chunk_text              TEXT,
    source_document_id      UUID,                          -- FK to documents if available
    -- Usage statistics
    retrieval_count         INTEGER DEFAULT 0,
    citation_count          INTEGER DEFAULT 0,
    citation_rate           FLOAT,
    -- Health
    last_retrieved_at       TIMESTAMPTZ,
    is_stale                BOOLEAN DEFAULT false,         -- citation_rate < 0.2 after 50+ retrievals
    staleness_reason        TEXT,
    -- Overlap analysis
    semantic_overlap_score  FLOAT,                         -- overlap with neighboring chunks
    -- From chunk optimizer
    optimal_chunk_size      INTEGER,
    size_recommendation     TEXT,
    UNIQUE(pipeline_id, chunk_id)
);
CREATE INDEX idx_chunks_pipeline ON chunk_stats(pipeline_id, is_stale);
```

### 3.5 documents
```sql
CREATE TABLE documents (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id             UUID REFERENCES pipelines(id) ON DELETE CASCADE,
    title                   VARCHAR(500) NOT NULL,
    source_url              TEXT,
    content_hash            VARCHAR(64),
    document_type           VARCHAR(100),
    -- Freshness
    last_modified_at        TIMESTAMPTZ,
    ingested_at             TIMESTAMPTZ DEFAULT NOW(),
    days_since_modified     INTEGER,
    freshness_status        VARCHAR(50) DEFAULT 'fresh'
                            CHECK (freshness_status IN
                            ('fresh', 'aging', 'stale', 'outdated', 'needs_review')),
    freshness_alert_sent    BOOLEAN DEFAULT false,
    -- Coverage
    topic_labels            JSONB,                         -- list of topic strings
    coverage_score          FLOAT,
    -- Quality
    chunk_count             INTEGER DEFAULT 0,
    stale_chunk_count       INTEGER DEFAULT 0,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_documents_pipeline ON documents(pipeline_id);
CREATE INDEX idx_documents_freshness ON documents(pipeline_id, freshness_status);
```

### 3.6 knowledge_gaps
```sql
CREATE TABLE knowledge_gaps (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id             UUID REFERENCES pipelines(id) ON DELETE CASCADE,
    -- Gap characterization
    topic_label             VARCHAR(500) NOT NULL,
    representative_query    TEXT,
    query_count             INTEGER DEFAULT 1,
    failure_rate            FLOAT,
    affected_users_estimate INTEGER DEFAULT 0,
    -- Business impact
    estimated_monthly_cost_usd FLOAT,
    priority                VARCHAR(50) DEFAULT 'medium'
                            CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    -- Fix
    suggested_document_topic TEXT,
    auto_fix_draft          TEXT,
    fix_format              VARCHAR(50) DEFAULT 'markdown'
                            CHECK (fix_format IN
                            ('markdown', 'confluence', 'notion', 'github_wiki', 'pdf')),
    -- State
    status                  VARCHAR(50) DEFAULT 'open'
                            CHECK (status IN ('open', 'acknowledged', 'in_progress', 'fixed')),
    fixed_at                TIMESTAMPTZ,
    trust_improvement_after_fix FLOAT,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_gaps_pipeline ON knowledge_gaps(pipeline_id, status, priority);
```

### 3.7 autofix_recommendations
```sql
CREATE TABLE autofix_recommendations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id             UUID REFERENCES pipelines(id) ON DELETE CASCADE,
    -- Classification
    rec_type                VARCHAR(100) NOT NULL
                            CHECK (rec_type IN (
                            'add_document', 'remove_stale_chunk', 'update_embedding_model',
                            'tune_retrieval', 'adjust_chunk_size', 'rewrite_prompt',
                            'adjust_top_k', 'change_retrieval_strategy')),
    priority                VARCHAR(50) NOT NULL
                            CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    -- Description
    title                   VARCHAR(500) NOT NULL,
    description             TEXT NOT NULL,
    -- Estimated impact (from fix planner)
    estimated_trust_improvement_pct FLOAT,
    estimated_cost_usd      FLOAT,
    estimated_hours         FLOAT,
    difficulty              VARCHAR(50)
                            CHECK (difficulty IN ('trivial', 'easy', 'medium', 'hard')),
    -- Action payload
    action_type             VARCHAR(100),
    action_parameters       JSONB,
    -- State
    status                  VARCHAR(50) DEFAULT 'open'
                            CHECK (status IN ('open', 'applied', 'dismissed', 'failed')),
    applied_at              TIMESTAMPTZ,
    applied_by_user_id      UUID REFERENCES users(id),
    verified_trust_improvement FLOAT,                     -- measured after apply
    created_at              TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_recs_pipeline ON autofix_recommendations(pipeline_id, status, priority);
```

### 3.8 retrieval_benchmarks
```sql
CREATE TABLE retrieval_benchmarks (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id             UUID REFERENCES pipelines(id) ON DELETE CASCADE,
    benchmark_name          VARCHAR(255) NOT NULL,
    -- Configuration
    test_queries            JSONB NOT NULL,                -- list of {query, expected_chunks}
    strategies_tested       JSONB NOT NULL,                -- list of strategy names
    -- Results
    results                 JSONB,
    -- list of {strategy, trust_score, latency_ms, cost_usd, hallucination_rate, precision, recall}
    winner_strategy         VARCHAR(100),
    winner_trust_score      FLOAT,
    status                  VARCHAR(50) DEFAULT 'pending'
                            CHECK (status IN ('pending', 'running', 'complete', 'failed')),
    started_at              TIMESTAMPTZ,
    completed_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.9 llm_comparisons
```sql
CREATE TABLE llm_comparisons (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id             UUID REFERENCES pipelines(id) ON DELETE CASCADE,
    comparison_name         VARCHAR(255) NOT NULL,
    test_queries            JSONB NOT NULL,
    models_tested           JSONB NOT NULL,                -- list of model names
    results                 JSONB,
    -- list of {model, trust_score, latency_p50_ms, cost_per_1k_usd, hallucination_rate, faithfulness}
    winner_model            VARCHAR(255),
    status                  VARCHAR(50) DEFAULT 'pending',
    completed_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.10 monitoring_configs
```sql
CREATE TABLE monitoring_configs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id             UUID REFERENCES pipelines(id) ON DELETE CASCADE UNIQUE,
    is_enabled              BOOLEAN DEFAULT false,
    interval_minutes        INTEGER DEFAULT 60,
    probe_queries           JSONB NOT NULL DEFAULT '[]',   -- list of probe query strings
    alert_trust_threshold   FLOAT DEFAULT 70.0,
    alert_hallucination_threshold FLOAT DEFAULT 0.10,
    alert_channels          JSONB DEFAULT '[]',            -- list of {type: "email"|"webhook", target}
    last_run_at             TIMESTAMPTZ,
    next_run_at             TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.11 monitoring_runs
```sql
CREATE TABLE monitoring_runs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id             UUID REFERENCES pipelines(id) ON DELETE CASCADE,
    config_id               UUID REFERENCES monitoring_configs(id),
    trust_score             FLOAT,
    hallucination_rate      FLOAT,
    probes_run              INTEGER,
    probes_failed           INTEGER,
    alerts_triggered        JSONB,
    regression_detected     BOOLEAN DEFAULT false,
    run_at                  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_monitoring_runs_pipeline ON monitoring_runs(pipeline_id, run_at DESC);
```

### 3.12 regression_snapshots
```sql
CREATE TABLE regression_snapshots (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id             UUID REFERENCES pipelines(id) ON DELETE CASCADE,
    snapshot_label          VARCHAR(255),                  -- "v1.2.0-deploy", "pre-reembed"
    trust_score             FLOAT NOT NULL,
    faithfulness_avg        FLOAT,
    context_precision_avg   FLOAT,
    hallucination_rate      FLOAT,
    trace_count             INTEGER,
    snapshot_at             TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_snapshots_pipeline ON regression_snapshots(pipeline_id, snapshot_at DESC);
```

### 3.13 knowledge_graph_nodes
```sql
CREATE TABLE knowledge_graph_nodes (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id             UUID REFERENCES pipelines(id) ON DELETE CASCADE,
    document_id             UUID REFERENCES documents(id),
    topic_label             VARCHAR(500) NOT NULL,
    node_type               VARCHAR(50)
                            CHECK (node_type IN ('document', 'topic', 'concept')),
    query_hit_count         INTEGER DEFAULT 0,
    coverage_strength       FLOAT DEFAULT 0.0,
    x_position              FLOAT,
    y_position              FLOAT,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.14 knowledge_graph_edges
```sql
CREATE TABLE knowledge_graph_edges (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id             UUID REFERENCES pipelines(id) ON DELETE CASCADE,
    source_node_id          UUID REFERENCES knowledge_graph_nodes(id) ON DELETE CASCADE,
    target_node_id          UUID REFERENCES knowledge_graph_nodes(id) ON DELETE CASCADE,
    relationship_type       VARCHAR(100),
    strength                FLOAT DEFAULT 1.0,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.15 synthetic_test_sets
```sql
CREATE TABLE synthetic_test_sets (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id             UUID REFERENCES pipelines(id) ON DELETE CASCADE,
    name                    VARCHAR(255) NOT NULL,
    source_documents        JSONB,
    questions               JSONB NOT NULL,
    -- list of {question, expected_answer, question_type, difficulty}
    question_types          JSONB,
    -- {faq: int, edge_case: int, adversarial: int, multi_hop: int, long_context: int}
    total_questions         INTEGER,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.16 integration_events
```sql
CREATE TABLE integration_events (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id             UUID REFERENCES pipelines(id) ON DELETE CASCADE,
    event_type              VARCHAR(100) NOT NULL,
    -- "trust_drop", "regression_detected", "knowledge_gap_created"
    target_system           VARCHAR(100),
    -- "agent_audit", "ghost_eval", "inference_forge", "embedding_drift", "privacy_lens"
    payload                 JSONB,
    webhook_url             TEXT,
    delivery_status         VARCHAR(50) DEFAULT 'pending',
    delivered_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 4. SDK

### 4.1 Core Tracer (`sdk/raginspector/tracer.py`)

```python
import functools
import time
import threading
import queue
import uuid
import httpx
from typing import Optional, Union

class RAGTracer:
    """
    Zero-code-change instrumentation for RAG pipelines.

    Usage — decorator mode:
        tracer = RAGTracer(api_key="ri_xxxxx", pipeline_id="uuid")

        @tracer.trace_retrieval
        def retrieve(query: str) -> list[dict]:
            ...  # must return list of {chunk_id, text, score}

        @tracer.trace_generation
        def generate(query: str, context: list[str]) -> str:
            ...  # must return answer string

    Usage — context manager mode:
        with tracer.trace("user question") as t:
            chunks = retrieve(query)
            t.set_chunks(chunks)
            answer = generate(query, chunks)
            t.set_answer(answer)
    """

    def __init__(
        self,
        api_key: str,
        pipeline_id: str,
        api_url: str = "https://api.raginspector.com",
        batch_size: int = 10,
        flush_interval_seconds: float = 2.0,
    ):
        self.api_key = api_key
        self.pipeline_id = pipeline_id
        self.api_url = api_url
        self.batch_size = batch_size
        self._current_trace: Optional[dict] = None
        self._queue: queue.Queue = queue.Queue()
        self._flush_thread = threading.Thread(
            target=self._flush_loop,
            args=(flush_interval_seconds,),
            daemon=True
        )
        self._flush_thread.start()

    # ─── Decorator API ────────────────────────────────────────────────────────

    def trace_retrieval(self, func):
        """Decorator: wraps retrieval function, captures chunks + latency."""
        @functools.wraps(func)
        def wrapper(query: str, *args, **kwargs):
            start = time.monotonic()
            result = func(query, *args, **kwargs)
            latency_ms = (time.monotonic() - start) * 1000
            self._current_trace = {
                "trace_id": str(uuid.uuid4()),
                "query_text": query,
                "retrieved_chunks": result if isinstance(result, list) else [],
                "retrieval_latency_ms": latency_ms,
            }
            return result
        return wrapper

    def trace_generation(self, func):
        """Decorator: wraps generation function, submits complete trace."""
        @functools.wraps(func)
        def wrapper(query: str, context, *args, **kwargs):
            start = time.monotonic()
            result = func(query, context, *args, **kwargs)
            gen_latency_ms = (time.monotonic() - start) * 1000
            if self._current_trace:
                retr_ms = self._current_trace.get("retrieval_latency_ms", 0)
                trace = {
                    **self._current_trace,
                    "generated_answer": result if isinstance(result, str) else str(result),
                    "generation_latency_ms": gen_latency_ms,
                    "total_latency_ms": retr_ms + gen_latency_ms,
                    "pipeline_id": self.pipeline_id,
                }
                self._queue.put(trace)
                self._current_trace = None
            return result
        return wrapper

    # ─── Context Manager API ──────────────────────────────────────────────────

    def trace(self, query: str, session_id: Optional[str] = None):
        """Context manager for manual tracing."""
        return _TraceContext(self, query, session_id)

    # ─── Internal ─────────────────────────────────────────────────────────────

    def _flush_loop(self, interval: float):
        while True:
            time.sleep(interval)
            batch = []
            try:
                while len(batch) < self.batch_size:
                    batch.append(self._queue.get_nowait())
            except queue.Empty:
                pass
            if batch:
                self._post_traces(batch)

    def _post_traces(self, traces: list):
        try:
            httpx.post(
                f"{self.api_url}/api/v1/traces/batch",
                json={"traces": traces},
                headers={"X-API-Key": self.api_key},
                timeout=10.0,
            )
        except Exception:
            pass  # Fire-and-forget; never block the production pipeline


class _TraceContext:
    def __init__(self, tracer: RAGTracer, query: str, session_id: Optional[str]):
        self._tracer = tracer
        self._data: dict = {
            "trace_id": str(uuid.uuid4()),
            "query_text": query,
            "pipeline_id": tracer.pipeline_id,
            "session_id": session_id,
        }
        self._start = time.monotonic()

    def set_chunks(self, chunks: list):
        self._data["retrieved_chunks"] = chunks
        self._data["retrieval_latency_ms"] = (time.monotonic() - self._start) * 1000

    def set_answer(self, answer: str, model: Optional[str] = None):
        self._data["generated_answer"] = answer
        self._data["llm_model"] = model
        self._data["generation_latency_ms"] = (
            (time.monotonic() - self._start) * 1000
            - self._data.get("retrieval_latency_ms", 0)
        )
        self._data["total_latency_ms"] = (time.monotonic() - self._start) * 1000

    def __enter__(self):
        return self

    def __exit__(self, *_):
        if "generated_answer" in self._data:
            self._tracer._queue.put(self._data)
```

### 4.2 Async Tracer (`sdk/raginspector/async_tracer.py`)

```python
import asyncio
import httpx
from raginspector.tracer import RAGTracer

class AsyncRAGTracer(RAGTracer):
    """
    Async version for FastAPI / async pipelines.

    Usage:
        tracer = AsyncRAGTracer(api_key="ri_xxxxx", pipeline_id="uuid")

        @tracer.async_trace_retrieval
        async def retrieve(query: str) -> list[dict]: ...

        @tracer.async_trace_generation
        async def generate(query: str, context) -> str: ...
    """

    def async_trace_retrieval(self, func):
        import functools, time
        @functools.wraps(func)
        async def wrapper(query: str, *args, **kwargs):
            start = time.monotonic()
            result = await func(query, *args, **kwargs)
            self._current_trace = {
                "query_text": query,
                "retrieved_chunks": result if isinstance(result, list) else [],
                "retrieval_latency_ms": (time.monotonic() - start) * 1000,
            }
            return result
        return wrapper

    def async_trace_generation(self, func):
        import functools, time
        @functools.wraps(func)
        async def wrapper(query: str, context, *args, **kwargs):
            start = time.monotonic()
            result = await func(query, context, *args, **kwargs)
            gen_ms = (time.monotonic() - start) * 1000
            if self._current_trace:
                retr_ms = self._current_trace.get("retrieval_latency_ms", 0)
                self._queue.put({
                    **self._current_trace,
                    "generated_answer": str(result),
                    "generation_latency_ms": gen_ms,
                    "total_latency_ms": retr_ms + gen_ms,
                    "pipeline_id": self.pipeline_id,
                })
                self._current_trace = None
            return result
        return wrapper
```

### 4.3 LangChain Integration (`sdk/raginspector/integrations/langchain.py`)

```python
from langchain_core.callbacks import BaseCallbackHandler
from raginspector.tracer import RAGTracer

class RAGInspectorCallback(BaseCallbackHandler):
    """
    Zero-code-change LangChain integration.

    Usage:
        chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            callbacks=[RAGInspectorCallback(api_key="ri_xxx", pipeline_id="uuid")]
        )
    """

    def __init__(self, api_key: str, pipeline_id: str):
        self.tracer = RAGTracer(api_key=api_key, pipeline_id=pipeline_id)
        self._pending: dict = {}
        self._query: str = ""

    def on_chain_start(self, serialized, inputs, **kwargs):
        self._query = inputs.get("query", inputs.get("question", ""))
        self._pending = {}

    def on_retriever_end(self, documents, **kwargs):
        self._pending["retrieved_chunks"] = [
            {
                "chunk_id": doc.metadata.get("id", f"chunk_{i}"),
                "text": doc.page_content,
                "score": doc.metadata.get("score", 0.0),
                "rank": i,
                "source_doc_id": doc.metadata.get("source", None),
            }
            for i, doc in enumerate(documents)
        ]

    def on_chain_end(self, outputs, **kwargs):
        if self._pending.get("retrieved_chunks") and self._query:
            self.tracer._queue.put({
                "query_text": self._query,
                "generated_answer": str(outputs.get("result", outputs.get("answer", ""))),
                "pipeline_id": self.tracer.pipeline_id,
                **self._pending,
            })
            self._pending = {}
            self._query = ""
```

### 4.4 LlamaIndex Integration (`sdk/raginspector/integrations/llamaindex.py`)

```python
from llama_index.core.callbacks import CallbackManager, CBEventType
from llama_index.core.callbacks.base_handler import BaseCallbackHandler
from raginspector.tracer import RAGTracer

class RAGInspectorLlamaHandler(BaseCallbackHandler):
    """
    Usage:
        callback_manager = CallbackManager([
            RAGInspectorLlamaHandler(api_key="ri_xxx", pipeline_id="uuid")
        ])
        index = VectorStoreIndex.from_documents(docs, callback_manager=callback_manager)
    """

    def __init__(self, api_key: str, pipeline_id: str):
        super().__init__(event_starts_to_ignore=[], event_ends_to_ignore=[])
        self.tracer = RAGTracer(api_key=api_key, pipeline_id=pipeline_id)
        self._pending: dict = {}

    def on_event_start(self, event_type, payload=None, **kwargs):
        if event_type == CBEventType.QUERY:
            self._pending["query_text"] = payload.get("query_str", "")

    def on_event_end(self, event_type, payload=None, **kwargs):
        if event_type == CBEventType.RETRIEVE:
            nodes = payload.get("nodes", [])
            self._pending["retrieved_chunks"] = [
                {"chunk_id": n.node_id, "text": n.text, "score": n.score or 0.0, "rank": i}
                for i, n in enumerate(nodes)
            ]
        if event_type == CBEventType.QUERY:
            if self._pending.get("retrieved_chunks"):
                self._pending["generated_answer"] = str(payload.get("response", ""))
                self._pending["pipeline_id"] = self.tracer.pipeline_id
                self.tracer._queue.put(dict(self._pending))
                self._pending = {}
```

### 4.5 Haystack Integration (`sdk/raginspector/integrations/haystack.py`)

```python
from haystack import component
from raginspector.tracer import RAGTracer

@component
class RAGInspectorComponent:
    """
    Wrap into a Haystack pipeline after the Generator step.

    Usage:
        pipeline.add_component("inspector",
            RAGInspectorComponent(api_key="ri_xxx", pipeline_id="uuid"))
        pipeline.connect("generator.replies", "inspector.answers")
        pipeline.connect("retriever.documents", "inspector.documents")
    """

    def __init__(self, api_key: str, pipeline_id: str):
        self.tracer = RAGTracer(api_key=api_key, pipeline_id=pipeline_id)

    @component.output_types(inspection_status=str)
    def run(self, query: str, documents: list, answers: list):
        self.tracer._queue.put({
            "query_text": query,
            "retrieved_chunks": [
                {"chunk_id": d.id, "text": d.content, "score": d.score or 0.0, "rank": i}
                for i, d in enumerate(documents)
            ],
            "generated_answer": answers[0].data if answers else "",
            "pipeline_id": self.tracer.pipeline_id,
        })
        return {"inspection_status": "queued"}
```

---

## 5. API ROUTES (Complete)

### 5.1 Auth (`/api/v1/auth`)

```
POST /api/v1/auth/register
  Body: { email, password, full_name }
  Response: { user_id, access_token, api_key }

POST /api/v1/auth/login
  Body: { email, password }
  Response: { access_token, plan, api_key }

GET /api/v1/auth/me
  Auth: Bearer JWT
  Response: { id, email, plan, api_key, plan_expires_at }

POST /api/v1/auth/rotate-key
  Auth: Bearer JWT
  Response: { api_key }    -- invalidates previous key
```

### 5.2 Pipelines (`/api/v1/pipelines`)

```
GET /api/v1/pipelines
  Auth: Bearer JWT
  Response: { pipelines: list[PipelineSummary] }

POST /api/v1/pipelines
  Body: { name, framework, description, queries_per_month, cost_per_wrong_answer_usd,
          embedding_model, chunk_size, chunk_overlap, top_k, retrieval_strategy }
  Response: { pipeline: Pipeline }

GET /api/v1/pipelines/{pipeline_id}
  Response: full Pipeline with aggregated metrics

PATCH /api/v1/pipelines/{pipeline_id}
  Body: partial Pipeline fields
  Response: updated Pipeline

DELETE /api/v1/pipelines/{pipeline_id}
  Response: { deleted: true }

POST /api/v1/pipelines/{pipeline_id}/snapshot
  Body: { label: "v1.2.0-pre-deploy" }
  Response: { snapshot: RegressionSnapshot }
  -- Saves current metrics as named baseline for regression comparison
```

### 5.3 Traces (`/api/v1/traces`)

```
POST /api/v1/traces/batch
  Headers: X-API-Key
  Body: {
    traces: list[{
      query_text, retrieved_chunks, generated_answer, pipeline_id,
      session_id?, llm_model?, total_latency_ms?, retrieval_latency_ms?, generation_latency_ms?
    }]
  }
  Response: { accepted: int, queued_for_analysis: int }
  -- Validates API key, stores traces, dispatches Celery tasks
  -- Rate limit: 100 traces/second per API key (Redis sliding window)

GET /api/v1/traces
  Auth: Bearer JWT
  Query: pipeline_id, failure_type?, start_date?, end_date?, limit=50, offset=0,
         min_trust_score?, max_trust_score?, session_id?
  Response: { traces: list[TraceSummary], total: int }

GET /api/v1/traces/{trace_id}
  Auth: Bearer JWT
  Response: {
    ...all trace fields,
    grounding_detail: list[{
      sentence: str,
      is_grounded: bool,
      supporting_chunk: { chunk_id, text, similarity_score, evidence_text } | null,
      confidence: float
    }],
    citation_detail: list[{
      sentence: str, citations: list[{ chunk_id, relevance, is_contradicting }]
    }],
    prompt_analysis: { issues: list[{ type, description, fix }], overall_score: float }
  }
```

### 5.4 Metrics (`/api/v1/metrics`)

```
GET /api/v1/metrics/dashboard
  Auth: Bearer JWT
  Query: pipeline_id
  Response: {
    trust_score: float,
    hallucination_cost_usd: float,
    faithfulness_avg: float,
    context_precision_avg: float,
    context_recall_avg: float,
    failure_breakdown: { retrieval_miss_pct, context_miss_pct, hallucination_pct },
    trend_30d: list[{ date, trust_score, faithfulness, hallucination_rate, failure_rate }],
    top_failing_queries: list[{ query, failure_type, count }],
    knowledge_coverage_pct: float,
    total_traces: int
  }

GET /api/v1/metrics/executive
  Auth: Bearer JWT (enterprise only)
  Query: pipeline_id
  Response: {
    trust_score: float,
    trust_trend: "improving" | "stable" | "degrading",
    hallucination_cost_usd: float,
    knowledge_coverage_pct: float,
    customer_impact_estimate: {
      support_tickets_at_risk: int,
      escalation_risk: float,
      revenue_risk_usd: float
    },
    ai_quality_trend_90d: list[{ date, trust_score }],
    peer_benchmark_percentile: float
  }

GET /api/v1/metrics/chunks
  Auth: Bearer JWT
  Query: pipeline_id, is_stale?, sort_by?
  Response: { chunks: list[ChunkStats], stale_count: int, healthy_count: int }

GET /api/v1/metrics/attribution/{trace_id}
  Auth: Bearer JWT
  Response: list of { sentence, supporting_chunk_id, confidence, evidence_text }
  -- Per-sentence answer attribution
```

### 5.5 Failures (`/api/v1/failures`)

```
GET /api/v1/failures/summary
  Auth: Bearer JWT
  Query: pipeline_id, days=7
  Response: {
    total_failures: int,
    by_type: { retrieval_miss: int, context_miss: int, hallucination: int },
    failure_rate: float,
    most_common_patterns: list[{ pattern, count, example_query, failure_type }]
  }

GET /api/v1/failures/patterns
  Auth: Bearer JWT
  Query: pipeline_id, days=30
  Response: clustered failure patterns with trend data
```

### 5.6 Knowledge (`/api/v1/knowledge`)

```
GET /api/v1/knowledge/gaps
  Auth: Bearer JWT
  Query: pipeline_id, status?, priority?
  Response: { gaps: list[KnowledgeGap], total_cost_usd: float }

POST /api/v1/knowledge/gaps/{gap_id}/generate-draft
  Auth: Bearer JWT (pro+)
  Body: { format: "markdown" | "confluence" | "notion" | "github_wiki" | "pdf" }
  Response: { draft: str, suggested_title: str, word_count: int, format: str }

PATCH /api/v1/knowledge/gaps/{gap_id}
  Body: { status: "acknowledged" | "in_progress" | "fixed" }
  Response: updated gap

GET /api/v1/knowledge/coverage-map
  Auth: Bearer JWT
  Query: pipeline_id
  Response: {
    coverage_pct: float,
    covered_topics: list[{ topic, strength, query_count }],
    missing_topics: list[{ topic, query_count, failure_rate }],
    weak_topics: list[{ topic, strength, suggested_improvement }]
  }

GET /api/v1/knowledge/freshness
  Auth: Bearer JWT
  Query: pipeline_id
  Response: {
    documents: list[{ id, title, days_since_modified, freshness_status, alert_reason }],
    stale_count: int,
    outdated_count: int
  }

GET /api/v1/knowledge/graph
  Auth: Bearer JWT (pro+)
  Query: pipeline_id
  Response: { nodes: list[Node], edges: list[Edge] }

POST /api/v1/knowledge/graph/rebuild
  Auth: Bearer JWT (pro+)
  Response: { job_id: str }   -- async rebuild
```

### 5.7 Auto-Fix (`/api/v1/autofix`)

```
GET /api/v1/autofix/recommendations
  Auth: Bearer JWT (pro+)
  Query: pipeline_id
  Response: {
    recommendations: list[{
      id, rec_type, priority, title, description,
      estimated_trust_improvement_pct, estimated_cost_usd, estimated_hours, difficulty,
      action_type, action_parameters, status
    }]
  }

POST /api/v1/autofix/apply/{recommendation_id}
  Auth: Bearer JWT (enterprise only)
  Response: { applied: bool, result: str }
  -- For auto-applicable fixes only (stale chunk removal, chunk size suggestion)

POST /api/v1/autofix/dismiss/{recommendation_id}
  Auth: Bearer JWT (pro+)
  Response: { dismissed: bool }
```

### 5.8 Benchmark (`/api/v1/benchmark`)

```
POST /api/v1/benchmark/retrieval
  Auth: Bearer JWT (pro+)
  Body: {
    pipeline_id, name, test_queries: list[{ query, expected_chunks? }],
    strategies: list["bm25" | "dense" | "hybrid" | "colbert" | "splade"]
  }
  Response: { benchmark_id: str, status: "running" }

GET /api/v1/benchmark/retrieval/{benchmark_id}
  Response: BenchmarkResult with per-strategy scores

POST /api/v1/benchmark/llm-comparison
  Auth: Bearer JWT (pro+)
  Body: {
    pipeline_id, name, test_queries,
    models: list["gpt-4o" | "claude-3-5-sonnet" | "gemini-1.5-pro" | "llama-3.1-70b" | ...]
  }
  Response: { comparison_id: str, status: "running" }

GET /api/v1/benchmark/llm-comparison/{comparison_id}
  Response: ComparisonResult with per-model metrics
```

### 5.9 Studio (`/api/v1/studio`)

```
POST /api/v1/studio/chunk-optimizer
  Auth: Bearer JWT (pro+)
  Body: {
    pipeline_id, test_queries,
    chunk_sizes: list[int],   -- e.g. [256, 512, 768, 1024]
    chunk_overlaps?: list[int]
  }
  Response: {
    results: list[{
      chunk_size, overlap, trust_score, latency_ms, cost_per_query_usd, hallucination_rate
    }],
    recommendation: { chunk_size, overlap, expected_trust_improvement }
  }

POST /api/v1/studio/retrieval-simulator
  Auth: Bearer JWT (pro+)
  Body: {
    pipeline_id, query,
    scenarios: list[{
      chunk_size?, embedding_model?, retrieval_strategy?, top_k?
    }]
  }
  Response: {
    scenarios: list[{
      config, predicted_trust_score, predicted_latency_ms,
      predicted_cost_usd, predicted_hallucination_rate
    }]
  }

POST /api/v1/studio/prompt-analyzer
  Auth: Bearer JWT (pro+)
  Body: { pipeline_id, prompt: str }
  Response: {
    overall_score: float,     -- 0-100
    issues: list[{
      type: "ambiguity" | "missing_context" | "conflicting_instructions" | "retrieval_inefficiency",
      description: str,
      severity: "high" | "medium" | "low",
      fix: str
    }],
    rewritten_prompt: str,
    improvement_explanation: str
  }
```

### 5.10 Monitoring (`/api/v1/monitoring`)

```
GET /api/v1/monitoring/config/{pipeline_id}
  Auth: Bearer JWT (pro+)
  Response: MonitoringConfig

PUT /api/v1/monitoring/config/{pipeline_id}
  Body: {
    is_enabled, interval_minutes, probe_queries,
    alert_trust_threshold, alert_hallucination_threshold, alert_channels
  }
  Response: updated MonitoringConfig

GET /api/v1/monitoring/history/{pipeline_id}
  Query: days=7
  Response: list[MonitoringRun]

POST /api/v1/monitoring/run-now/{pipeline_id}
  Auth: Bearer JWT (enterprise)
  Response: { run_id: str }   -- triggers immediate probe run
```

### 5.11 Regression (`/api/v1/regression`)

```
GET /api/v1/regression/snapshots/{pipeline_id}
  Auth: Bearer JWT
  Response: list[RegressionSnapshot]

POST /api/v1/regression/compare
  Auth: Bearer JWT (pro+)
  Body: { pipeline_id, baseline_snapshot_id, compare_to: "current" | snapshot_id }
  Response: {
    baseline: RegressionSnapshot,
    current: RegressionSnapshot,
    delta: {
      trust_score_delta: float,
      faithfulness_delta: float,
      hallucination_rate_delta: float,
      is_regression: bool,
      regression_severity: "none" | "minor" | "major" | "critical",
      recommendation: str
    }
  }

POST /api/v1/regression/pre-deploy-check
  Auth: Bearer JWT (enterprise)
  Body: { pipeline_id, deploy_label: str }
  Response: {
    passed: bool,
    trust_score: float,
    baseline_trust_score: float,
    regression_risk: "low" | "medium" | "high",
    blocking_issues: list[str]
  }
  -- Returns 200 pass / 422 block-deploy based on regression severity
```

### 5.12 Synthetic Test Sets (`/api/v1/testsets`)

```
POST /api/v1/testsets/generate
  Auth: Bearer JWT (pro+)
  Body: {
    pipeline_id, name,
    source_documents?: list[str],   -- doc IDs or raw text
    question_types: {
      faq?: int, edge_case?: int, adversarial?: int, multi_hop?: int, long_context?: int
    },
    total_questions: int
  }
  Response: { testset_id: str, status: "generating" }

GET /api/v1/testsets/{testset_id}
  Response: SyntheticTestSet with all questions

POST /api/v1/testsets/{testset_id}/run
  Auth: Bearer JWT (pro+)
  Response: { run_id: str }   -- runs test set against pipeline, creates traces
```

### 5.13 AI Investigator (`/api/v1/investigator`)

```
POST /api/v1/investigator/query
  Auth: Bearer JWT (pro+)
  Body: { pipeline_id, question: str }
  -- "Why did Trust Score drop this week?"
  -- "What caused the hallucination spike on Monday?"
  -- "Which documents are causing the most failures?"
  Response: {
    answer: str,              -- natural language explanation
    supporting_data: list[{
      metric: str, value: float | str, change: str, timestamp: str
    }],
    recommended_actions: list[str]
  }
```

### 5.14 Reports (`/api/v1/reports`)

```
POST /api/v1/reports/generate
  Auth: Bearer JWT (pro+)
  Body: {
    pipeline_id,
    report_type: "quality_summary" | "executive_brief" | "technical_deep_dive",
    format: "pdf" | "json",
    date_range: { start, end }
  }
  Response: { report_url: str } (PDF) or { report: dict } (JSON)

POST /api/v1/reports/export-gap-docs
  Auth: Bearer JWT (pro+)
  Body: {
    pipeline_id,
    gap_ids: list[str],
    format: "markdown" | "confluence" | "notion" | "github_wiki"
  }
  Response: { export_url: str } or { content: str }
```

### 5.15 Billing (`/api/v1/billing`)

```
POST /api/v1/billing/create-subscription
  Auth: Bearer JWT
  Body: { plan: "pro" | "enterprise" }
  Response: { razorpay_order_id: str, razorpay_key_id: str, amount: int }

POST /api/v1/billing/verify-payment
  Body: { razorpay_payment_id, razorpay_order_id, razorpay_signature }
  Response: { success: bool, plan: str, expires_at: str }

POST /api/v1/billing/webhook
  Headers: X-Razorpay-Signature
  Body: Razorpay webhook payload
  -- Handles subscription.activated, subscription.cancelled, payment.failed

GET /api/v1/billing/subscription
  Auth: Bearer JWT
  Response: { plan, status, expires_at, traces_used_this_month, traces_limit }
```

---

## 6. CORE SERVICES

### 6.1 Grounding Service (`backend/app/services/grounding.py`)

```python
from sentence_transformers import CrossEncoder
import re

_nli_model = None

def get_nli_model() -> CrossEncoder:
    global _nli_model
    if _nli_model is None:
        # 85MB, CPU-only, < 100ms per batch
        _nli_model = CrossEncoder('cross-encoder/nli-deberta-v3-small')
    return _nli_model

def check_grounding(answer: str, chunks: list[dict]) -> list[dict]:
    """
    Sentence-level NLI grounding.

    Algorithm:
    1. Split answer into sentences
    2. For each sentence × each chunk: run NLI
    3. entailment score = scores[:, 2] (entailment column)
    4. Best chunk = argmax(entailment_scores)
    5. is_grounded = best_score > 0.5

    Returns:
        list of {
            sentence: str,
            is_grounded: bool,
            supporting_chunk_id: str | None,
            confidence: float,
            evidence_text: str | None   -- substring of chunk that supports sentence
        }
    """
    model = get_nli_model()
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', answer) if len(s.strip()) > 10]
    if not sentences or not chunks:
        return []

    results = []
    chunk_texts = [c.get("text", "") for c in chunks]
    chunk_ids = [c.get("chunk_id", f"chunk_{i}") for i, c in enumerate(chunks)]

    # Batch: all (chunk, sentence) pairs in one call
    pairs = [(ct, s) for s in sentences for ct in chunk_texts]
    scores = model.predict(pairs)           # shape: [len(sentences)*len(chunks), 3]
    entailment_scores = scores[:, 2]        # column 2 = entailment

    n_chunks = len(chunks)
    for i, sentence in enumerate(sentences):
        row = entailment_scores[i * n_chunks:(i + 1) * n_chunks]
        best_idx = int(row.argmax())
        best_score = float(row[best_idx])
        is_grounded = best_score > 0.5
        results.append({
            "sentence": sentence,
            "is_grounded": is_grounded,
            "supporting_chunk_id": chunk_ids[best_idx] if is_grounded else None,
            "confidence": best_score,
            "evidence_text": chunk_texts[best_idx][:200] if is_grounded else None,
        })

    return results

def compute_grounding_rate(grounding_results: list[dict]) -> float:
    if not grounding_results:
        return 0.0
    return sum(1 for r in grounding_results if r["is_grounded"]) / len(grounding_results)
```

### 6.2 Failure Classifier (`backend/app/services/failure_classifier.py`)

```python
def classify_failure(
    faithfulness: float,
    grounding_rate: float,
    context_precision: float,
    context_recall: float,
    answer_relevance: float,
) -> tuple[str | None, str, float]:
    """
    Returns: (failure_type, reason, confidence)

    Rules (evaluated in priority order):

    1. faithfulness < 0.5 AND grounding_rate < 0.5
       → "hallucination"
       → "Answer contains ungrounded claims not supported by retrieved context"
       → confidence = 1.0 - (faithfulness + grounding_rate) / 2

    2. context_precision < 0.3 OR context_recall < 0.4
       → "retrieval_miss"
       → "Retrieval returned mostly irrelevant chunks" (precision)
          OR "Retrieval failed to surface relevant documents" (recall)
       → confidence = 1.0 - max(context_precision, context_recall)

    3. faithfulness > 0.7 AND answer_relevance < 0.5
       → "context_miss"
       → "Retrieved context does not contain information needed to answer query"
       → confidence = 1.0 - answer_relevance

    4. All scores > 0.7
       → None, "", 1.0

    Default fallback:
       → "context_miss", "Insufficient signal to classify; defaulting to context miss", 0.5
    """
    if faithfulness < 0.5 and grounding_rate < 0.5:
        conf = 1.0 - (faithfulness + grounding_rate) / 2
        return "hallucination", "Answer contains ungrounded claims not supported by retrieved context", conf

    if context_precision < 0.3:
        return "retrieval_miss", "Retrieval returned mostly irrelevant chunks", 1.0 - context_precision

    if context_recall < 0.4:
        return "retrieval_miss", "Retrieval failed to surface relevant documents", 1.0 - context_recall

    if faithfulness > 0.7 and answer_relevance < 0.5:
        return "context_miss", "Retrieved context lacks information to answer this query", 1.0 - answer_relevance

    if faithfulness > 0.7 and grounding_rate > 0.7 and context_precision > 0.7:
        return None, "", 1.0

    return "context_miss", "Insufficient signal for precise classification; defaulting to context miss", 0.5
```

### 6.3 Trust Scorer (`backend/app/services/trust_scorer.py`)

```python
import statistics

def compute_trust_score(recent_traces: list) -> float:
    """
    Composite score 0–100 from last 100 complete traces.

    Components (sum = 100 points):
    - faithfulness_component    = mean(faithfulness) × 30
    - grounding_component       = mean(grounding_rate) × 30
    - retrieval_component       = mean(context_precision) × 20
    - reliability_component     = (1 - failure_rate) × 20

    Minimum traces: 5 (returns None if fewer)
    """
    traces = [t for t in recent_traces if t.analysis_status == "complete"]
    if len(traces) < 5:
        return None

    faithfulness_scores = [t.faithfulness for t in traces if t.faithfulness is not None]
    grounding_rates = [t.grounding_rate for t in traces if t.grounding_rate is not None]
    precision_scores = [t.context_precision for t in traces if t.context_precision is not None]
    failure_count = sum(1 for t in traces if t.failure_type is not None)

    faith = statistics.mean(faithfulness_scores) if faithfulness_scores else 0.0
    ground = statistics.mean(grounding_rates) if grounding_rates else 0.0
    precision = statistics.mean(precision_scores) if precision_scores else 0.0
    reliability = 1.0 - (failure_count / len(traces))

    score = (faith * 30) + (ground * 30) + (precision * 20) + (reliability * 20)
    return round(min(100.0, max(0.0, score)), 1)
```

### 6.4 Hallucination Cost (`backend/app/services/hallucination_cost.py`)

```python
def estimate_hallucination_cost(
    queries_per_month: int,
    cost_per_wrong_answer_usd: float,
    recent_traces: list,
) -> dict:
    """
    Returns detailed cost breakdown.
    """
    total = len(recent_traces)
    hallucinations = sum(1 for t in recent_traces if t.failure_type == "hallucination")
    retrieval_misses = sum(1 for t in recent_traces if t.failure_type == "retrieval_miss")
    context_misses = sum(1 for t in recent_traces if t.failure_type == "context_miss")

    hallucination_rate = hallucinations / total if total else 0.0
    retrieval_miss_rate = retrieval_misses / total if total else 0.0
    context_miss_rate = context_misses / total if total else 0.0
    total_failure_rate = (hallucinations + retrieval_misses + context_misses) / total if total else 0.0

    monthly_hallucinations = queries_per_month * hallucination_rate
    monthly_failures = queries_per_month * total_failure_rate

    return {
        "monthly_hallucination_cost_usd": round(monthly_hallucinations * cost_per_wrong_answer_usd, 2),
        "monthly_total_failure_cost_usd": round(monthly_failures * cost_per_wrong_answer_usd, 2),
        "hallucination_rate": round(hallucination_rate, 4),
        "retrieval_miss_rate": round(retrieval_miss_rate, 4),
        "context_miss_rate": round(context_miss_rate, 4),
        "monthly_hallucinations": round(monthly_hallucinations),
        "monthly_failures": round(monthly_failures),
    }
```

### 6.5 Fix Planner (`backend/app/services/fix_planner.py`)

```python
FIX_CATALOG = {
    "add_document": {
        "difficulty": "medium",
        "base_hours": 4.0,
        "base_cost_usd": 0.0,
        "trust_improvement_formula": lambda gap: min(15.0, gap.query_count * 0.3),
    },
    "remove_stale_chunk": {
        "difficulty": "trivial",
        "base_hours": 0.5,
        "base_cost_usd": 0.0,
        "trust_improvement_formula": lambda n: min(5.0, n * 0.5),
    },
    "update_embedding_model": {
        "difficulty": "hard",
        "base_hours": 16.0,
        "base_cost_usd": 50.0,
        "trust_improvement_formula": lambda _: 8.0,
    },
    "adjust_chunk_size": {
        "difficulty": "easy",
        "base_hours": 2.0,
        "base_cost_usd": 5.0,
        "trust_improvement_formula": lambda _: 6.0,
    },
    "change_retrieval_strategy": {
        "difficulty": "medium",
        "base_hours": 8.0,
        "base_cost_usd": 10.0,
        "trust_improvement_formula": lambda _: 10.0,
    },
    "rewrite_prompt": {
        "difficulty": "easy",
        "base_hours": 1.0,
        "base_cost_usd": 0.0,
        "trust_improvement_formula": lambda _: 5.0,
    },
}

def plan_fix(rec_type: str, context: dict) -> dict:
    """
    Returns: { difficulty, estimated_hours, estimated_cost_usd, estimated_trust_improvement_pct }
    """
    template = FIX_CATALOG.get(rec_type, {
        "difficulty": "medium", "base_hours": 4.0, "base_cost_usd": 0.0,
        "trust_improvement_formula": lambda _: 5.0,
    })
    return {
        "difficulty": template["difficulty"],
        "estimated_hours": template["base_hours"],
        "estimated_cost_usd": template["base_cost_usd"],
        "estimated_trust_improvement_pct": round(template["trust_improvement_formula"](context), 1),
    }
```

### 6.6 Knowledge Gap Detector (`backend/app/services/knowledge_gap.py`)

```python
from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN
import numpy as np

_embed_model = None

def get_embed_model():
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embed_model

def detect_knowledge_gaps(failed_traces: list) -> list[dict]:
    """
    Cluster failed queries to identify missing knowledge topics.

    Algorithm:
    1. Filter traces where failure_type in ('retrieval_miss', 'context_miss')
    2. Embed all query_text with sentence-transformers
    3. DBSCAN clustering (eps=0.3, min_samples=3)
    4. For each cluster: pick representative query, compute failure_rate, count
    5. LLM call (Groq/Ollama): "Given these queries that failed: {queries},
       what document topic is missing from the knowledge base?
       Return: { topic_label, suggested_document_title, key_subtopics }"
    6. Return gap records ordered by query_count desc

    Returns:
        list of {
            topic_label, representative_query, query_count,
            failure_rate, suggested_document_topic, priority
        }
    """
    if not failed_traces:
        return []

    model = get_embed_model()
    queries = [t.query_text for t in failed_traces]
    embeddings = model.encode(queries)

    clustering = DBSCAN(eps=0.3, min_samples=3, metric='cosine').fit(embeddings)
    labels = clustering.labels_

    gaps = []
    for label in set(labels):
        if label == -1:
            continue
        cluster_indices = np.where(labels == label)[0]
        cluster_traces = [failed_traces[i] for i in cluster_indices]
        representative = cluster_traces[0].query_text
        failure_rate = len(cluster_traces) / len(failed_traces)

        priority = "critical" if len(cluster_traces) > 50 else \
                   "high" if len(cluster_traces) > 20 else \
                   "medium" if len(cluster_traces) > 5 else "low"

        gaps.append({
            "topic_label": f"Missing coverage: {representative[:80]}",
            "representative_query": representative,
            "query_count": len(cluster_traces),
            "failure_rate": round(failure_rate, 3),
            "priority": priority,
        })

    return sorted(gaps, key=lambda g: g["query_count"], reverse=True)
```

### 6.7 Prompt Analyzer (`backend/app/services/prompt_analyzer.py`)

```python
PROMPT_ANALYSIS_SYSTEM = """
You are an expert RAG prompt engineer. Analyze the given prompt template for:
1. ambiguity — vague instructions the LLM could interpret multiple ways
2. missing_context — instructions that assume context that may not be in retrieved chunks
3. conflicting_instructions — instructions that contradict each other
4. retrieval_inefficiency — prompt structure that makes poor use of retrieved context

Return ONLY valid JSON:
{
  "overall_score": <0-100>,
  "issues": [
    {
      "type": "ambiguity" | "missing_context" | "conflicting_instructions" | "retrieval_inefficiency",
      "description": "<what is wrong>",
      "severity": "high" | "medium" | "low",
      "fix": "<specific rewrite suggestion>"
    }
  ],
  "rewritten_prompt": "<improved version>",
  "improvement_explanation": "<2-3 sentences>"
}
"""

async def analyze_prompt(prompt: str) -> dict:
    """
    Call Ollama (local) or Groq (fallback) to analyze prompt quality.
    Returns parsed dict from PROMPT_ANALYSIS_SYSTEM schema.
    """
    # Implementation uses httpx to call Ollama /api/generate or Groq /chat/completions
    # Parse JSON response and return
    ...
```

### 6.8 AI Investigator (`backend/app/services/ai_investigator.py`)

```python
AI_INVESTIGATOR_SYSTEM = """
You are the AI Investigator for RAGInspector. You answer natural language questions
about a RAG pipeline's quality metrics and failures.

You have access to: trust score history, hallucination rates, failure types, 
knowledge gaps, chunk statistics, and recent trace data.

Be specific and data-driven. Always cite the specific metric or event that caused
the observed change. Recommend concrete actions.

Return ONLY valid JSON:
{
  "answer": "<natural language explanation>",
  "supporting_data": [
    { "metric": str, "value": str, "change": str, "timestamp": str }
  ],
  "recommended_actions": [str, ...]
}
"""

async def investigate(question: str, pipeline_context: dict) -> dict:
    """
    Builds context from pipeline metrics, then calls LLM to explain.

    pipeline_context includes:
    - trust_score_trend (last 14 days)
    - recent_failure_counts (by type, last 7 days)
    - top_knowledge_gaps
    - recent_chunk_stats
    - recent_monitoring_runs
    """
    ...
```

---

## 7. WORKERS

### 7.1 RAGAS Worker (`backend/app/workers/ragas_worker.py`)

```python
@celery_app.task(name="compute_ragas", bind=True, max_retries=3)
def compute_ragas_task(self, trace_id: str):
    """
    1. Fetch trace from DB
    2. Run NLI grounding (CPU, sync):
       grounding_results = check_grounding(trace.generated_answer, trace.retrieved_chunks)
       grounding_rate = compute_grounding_rate(grounding_results)
    3. Compute context_precision heuristic:
       precision = fraction of retrieved chunks whose text appears (substring) in answer
       (LLM judge version for pro+ users via separate task)
    4. Compute context_recall heuristic:
       recall = grounding_rate (proxy — full RAGAS needs ground truth)
    5. Compute answer_relevance (BM25 similarity between query and answer)
    6. Classify failure type via classify_failure()
    7. Compute citation quality (citation_scorer.py)
    8. Update trace record with all metrics
    9. Update pipeline aggregated metrics (running average, last 100 traces)
    10. Update chunk_stats (increment retrieval_count, citation_count per cited chunk)
    11. Trigger knowledge_gap_check task if failure_type != None
    12. Check monitoring thresholds → trigger alert if crossed
    """
```

### 7.2 Monitoring Worker (`backend/app/workers/monitoring_worker.py`)

```python
@celery_app.task(name="run_monitoring_probes")
def run_monitoring_probes():
    """
    Scheduled Celery beat task (runs every minute, filters by next_run_at).

    For each enabled monitoring config due for a run:
    1. Run each probe_query against the SDK ingest endpoint (simulated trace)
    2. Wait for analysis completion (poll analysis_status, max 60s)
    3. Compute probe trust_score and hallucination_rate
    4. Compare against alert thresholds
    5. If threshold crossed: send alert via configured channel (email/webhook)
    6. Create monitoring_run record
    7. Update next_run_at = NOW() + interval_minutes
    """
```

### 7.3 Freshness Worker (`backend/app/workers/freshness_worker.py`)

```python
@celery_app.task(name="check_document_freshness")
def check_document_freshness(pipeline_id: str):
    """
    Runs daily per pipeline.

    1. For each document: compute days_since_modified
    2. Classify freshness_status:
       - fresh:        days < 30
       - aging:        30 <= days < 90
       - stale:        90 <= days < 180
       - outdated:     180 <= days < 365
       - needs_review: days >= 365
    3. For status 'outdated' or 'needs_review': create knowledge_gap alert
    4. Send email alert for documents crossing stale threshold (first time only)
    """
```

### 7.4 Regression Worker (`backend/app/workers/regression_worker.py`)

```python
@celery_app.task(name="check_regression")
def check_regression_task(pipeline_id: str, snapshot_label: str = None):
    """
    Triggered by: POST /api/v1/regression/pre-deploy-check

    1. Compute current Trust Score from last 100 traces
    2. Load baseline snapshot (most recent, or specified by snapshot_id)
    3. Compute deltas: trust_score, faithfulness, hallucination_rate
    4. Classify regression severity:
       - none:     delta > -2.0
       - minor:    -5.0 < delta <= -2.0
       - major:    -10.0 < delta <= -5.0
       - critical: delta <= -10.0
    5. Return pass/block recommendation
    """
```

---

## 8. FRONTEND — Complete Page Specifications

### UI Token System

```css
/* Design tokens — dark enterprise theme */
--color-bg-base:      #0D0F14;   /* Page background */
--color-bg-surface:   #141720;   /* Cards, panels */
--color-bg-elevated:  #1C2030;   /* Modals, dropdowns */
--color-border:       #2A2F45;   /* Dividers */
--color-text-primary: #E8ECF4;   /* Main text */
--color-text-muted:   #7B849E;   /* Labels, secondary */
--color-accent:       #00D4FF;   /* Primary CTA, highlights */
--color-success:      #00E676;   /* Grounded sentences, pass states */
--color-warning:      #FFB800;   /* Aging documents, medium severity */
--color-error:        #FF4B4B;   /* Hallucinations, failures, cost */
--color-trust-high:   #00E676;   /* Trust Score 80+ */
--color-trust-mid:    #FFB800;   /* Trust Score 60–80 */
--color-trust-low:    #FF4B4B;   /* Trust Score < 60 */
```

### 8.1 Dashboard (`/dashboard`)

```
LAYOUT: 4-column grid header cards, 2-column main content, full-width trend chart

TOP CARDS:
  [Trust Score Gauge] [Hallucination Cost] [Knowledge Coverage] [Active Failures]

TRUST SCORE GAUGE (hero):
  Circular SVG gauge, 0–100
  Color: --color-trust-high/mid/low based on value
  Shows: current value, 7d delta (+/-), trend arrow
  Click: navigates to /traces with filter failure_type=all

HALLUCINATION COST CARD:
  "$2,340/month" in --color-error, large
  Subtext: "4.2% rate × 10,000 queries × $5.00/wrong answer"
  Pencil icon: inline edit of cost_per_wrong_answer
  Shows: monthly hallucinations, monthly failures

KNOWLEDGE COVERAGE CARD:
  Stacked bar: Covered (green) / Weak (amber) / Missing (red)
  Percentage label
  Click: navigates to /knowledge/map

ACTIVE FAILURES CARD:
  Count of open autofix recommendations (critical + high)
  Click: navigates to /autofix

MAIN GRID (2-column):
  LEFT: Failure Breakdown pie chart (Recharts)
         Colors: retrieval_miss=#00D4FF, context_miss=#FFB800, hallucination=#FF4B4B
  RIGHT: Top Failing Queries table
         Columns: Query, Failure Type, Count, Last Seen

TREND CHART (full width):
  Recharts LineChart
  Lines: Trust Score (--color-accent), Faithfulness (--color-success), Failure Rate (--color-error)
  Date range selector: 7d / 30d / 90d
```

### 8.2 Trace Detail (`/traces/[id]`)

```
HERO: GROUNDING VISUALIZATION
  Answer text rendered sentence-by-sentence:
    Grounded sentence: green underline + hoverable
    Ungrounded sentence: red background + ⚠ icon
    Hover/click sentence → right panel highlights supporting chunk

  RIGHT PANEL: Retrieved Chunks
    Each chunk as card: chunk_id, score badge, text excerpt
    Highlighted (blue border) when its sentence is hovered
    Unused chunks: dimmed with "not cited" badge

METRICS ROW:
  Faithfulness: 0.91  |  Context Precision: 0.74  |  Grounding Rate: 87%  |  Latency: 342ms

FAILURE CLASSIFICATION BANNER:
  Green: "✓ No Failure Detected — Trust contribution: +1.2 pts"
  Red:   "✗ Retrieval Miss — Query: 'OAuth token refresh' not covered. Confidence: 0.89"

CITATION QUALITY SECTION:
  Citation Completeness: 0.84
  Unsupported Claims: 2  (click to highlight in grounding view)
  Contradicting Citations: 0

PROMPT ANALYSIS (collapsible):
  Overall Prompt Score: 72/100
  Issues list with severity badges and fix suggestions

QUERY INFO FOOTER:
  Query, Model, Latency breakdown (retrieval / generation), Session ID, Timestamp
```

### 8.3 Knowledge Coverage Map (`/knowledge/map`)

```
COVERAGE SUMMARY HEADER:
  Total Coverage: 78%  |  Covered Topics: 34  |  Missing: 8  |  Weak: 4

COVERAGE BAR VISUALIZATION:
  Full-width stacked bar per topic cluster
  Covered (green) / Weak (amber) / Missing (red)
  Hover bar → popover: topic name, query count, failure rate, suggested action
  Click topic → opens /knowledge/gaps filtered to that topic

TOPIC GRID (below):
  Cards per topic: name, strength meter, query hits, action button
  "Generate Doc" button on missing topics (opens draft flow)
  "Strengthen" button on weak topics (suggests related docs to add)
```

### 8.4 Knowledge Gaps (`/knowledge/gaps`)

```
FILTER BAR: priority filter, status filter, search

GAP CARDS (sorted by priority desc, then query_count desc):
  🔴 CRITICAL: [topic_label]
    "47 queries failed in last 7 days — Est. cost: $235/month"
    [Generate Draft ▾]  [Mark In Progress]  [Mark Fixed]
    Generate Draft dropdown: Markdown / Confluence / Notion / GitHub Wiki / PDF

  🟡 HIGH: [topic_label]
    "23 queries failing — Est. cost: $115/month"
    ...

DRAFT MODAL (on Generate Draft):
  Shows AI-generated document draft
  Copy / Download / Export to Confluence / Export to Notion
  Edit inline before export
```

### 8.5 Auto-Fix (`/autofix`)

```
TOTAL IMPACT HEADER:
  "Applying all recommendations could improve Trust Score by +12.4 pts"
  "Estimated time: 28 hours | Estimated cost: $65"

RECOMMENDATIONS LIST (sorted by priority):

  🔴 CRITICAL | Add Document: "OAuth Refresh Token Flow"
    "47 queries failed, zero retrieval matches — Est. +8.2 Trust pts"
    Priority: Critical  |  Difficulty: Medium  |  Est. 4h  |  Est. cost: $0
    [Generate Draft]  [Dismiss]

  🟡 HIGH | Remove 8 Stale Chunks
    "citation_rate < 5% after 100+ retrievals — polluting context"
    Priority: High  |  Difficulty: Trivial  |  Est. 30min  |  Est. cost: $0
    [Preview Chunks]  [Remove All]  [Dismiss]

  🔵 MEDIUM | Switch to Hybrid Retrieval
    "Benchmark shows hybrid outperforms dense by 6.1 Trust pts on this pipeline"
    Priority: Medium  |  Difficulty: Medium  |  Est. 8h  |  Est. cost: $10
    [View Benchmark]  [Dismiss]
```

### 8.6 Chunk Optimization Studio (`/studio/chunks`)

```
CONFIG PANEL:
  Chunk sizes to test: [256] [512] [768] [1024] + custom
  Chunk overlap: 0 / 25 / 50 / 100
  Test queries: textarea (enter representative queries) or [Use Top Failing Queries]
  [Run Optimization]

RESULTS TABLE (after run):
  Chunk Size | Overlap | Trust Score | Latency | Cost/Query | Hallucination Rate
  Highlight winning row in green
  Differences from current config shown as deltas

APPLY RECOMMENDATION CTA:
  "Apply 512-token chunks → Expected +4.2 Trust Score improvement"
  [Apply to Pipeline Config]
```

### 8.7 Retrieval Simulator (`/studio/simulator`)

```
SCENARIO BUILDER:
  Base query: [input field]
  Scenarios (add up to 5):
    Scenario 1: chunk_size=512, top_k=5, strategy=dense, embedding=text-embedding-3-small
    Scenario 2: chunk_size=256, top_k=10, strategy=hybrid, embedding=...
    [+ Add Scenario]
  [Run Simulation]

RESULTS COMPARISON:
  Side-by-side cards per scenario:
    Predicted Trust Score (large number)
    Predicted Latency, Cost/Query, Hallucination Rate
  Winner highlighted with green border
  [Apply Winner Config]
```

### 8.8 Retrieval Benchmark (`/benchmark/retrieval`)

```
CONFIGURATION:
  Name: [input]
  Strategies: BM25 ☑ | Dense ☑ | Hybrid ☑ | ColBERT ☐ | SPLADE ☐
  Test queries: enter manually or [Generate from Knowledge Gaps]
  [Run Benchmark]

RESULTS:
  Bar chart: Trust Score per strategy
  Table: Strategy | Trust Score | Latency P50 | Cost/Query | Precision | Recall
  Winner badge on best row
  [Apply Winner Strategy to Pipeline]
```

### 8.9 Multi-LLM Comparison (`/benchmark/models`)

```
MODEL SELECTOR:
  GPT-4o ☑ | Claude 3.5 Sonnet ☑ | Gemini 1.5 Pro ☑
  Llama 3.1 70B ☑ | DeepSeek V2 ☐ | Qwen 2.5 72B ☐
  [Add Custom Model via API URL]
  Test queries: [same as benchmark]
  [Run Comparison]

RESULTS MATRIX:
  Table: Model | Trust Score | Latency P50 | Cost/1K Queries | Hallucination Rate | Faithfulness
  Heatmap coloring: green = best, red = worst per column
  Recommendation: "Claude 3.5 Sonnet offers best Trust Score at $0.023/query"
```

### 8.10 Continuous Monitoring (`/monitoring`)

```
CONFIG CARD (per pipeline):
  Enable monitoring: toggle
  Check interval: 15min / 30min / 1h / 6h
  Probe queries: list editor (add/remove test questions)
  Alert if Trust Score < [70] or Hallucination Rate > [10%]
  Alert channels: Email [input] | Webhook [input]
  [Save Config]  [Run Now]

MONITORING HISTORY:
  Table: Run Time | Trust Score | Probes Run | Probes Failed | Alerts | Regression?
  Last 30 runs
  Click row → see individual probe trace results
```

### 8.11 AI Investigator (`/investigator`)

```
CHAT INTERFACE (full-height):
  Message bubbles, dark theme
  User types natural language questions about their pipeline

EXAMPLE QUESTIONS (shown on empty state):
  "Why did Trust Score drop this week?"
  "Which documents are causing the most hallucinations?"
  "What would improve my Trust Score the most right now?"
  "Show me what changed between Monday and Thursday"

ANSWER FORMAT:
  Natural language explanation + supporting_data table
  Recommended actions as clickable chips (e.g. "Go to Auto-Fix →")
```

### 8.12 Executive Dashboard (`/executive` — enterprise only)

```
CLEAN LAYOUT — NO engineering metrics visible

HERO ROW:
  Trust Score: 91/100  ↑ (+4.2 from last week)
  Hallucination Cost: $2,340/month  ↓ (-$420 from last month)
  Knowledge Coverage: 78%  ↑ (+5% from last month)

CUSTOMER IMPACT BOX:
  Estimated Support Tickets at Risk: 34/month
  Escalation Risk: 12%
  Estimated Revenue Risk: $11,700/month

AI QUALITY TREND (90-day chart):
  Single line: Trust Score
  Annotations: "Reindexed KB" | "New embedding model" | "Added OAuth docs"

PEER BENCHMARK (if enabled):
  "Your RAG quality is in the 74th percentile for SaaS companies in your industry"

EXPORT: [Download Executive Brief PDF]
```

---

## 9. RAGAS WORKER — COMPLETE ALGORITHM

```python
@celery_app.task(name="compute_ragas", bind=True, max_retries=3)
def compute_ragas_task(self, trace_id: str):
    """
    Full algorithm — executed async, never blocks SDK ingest.

    STEP 1: Fetch trace
    trace = db.query(QueryTrace).filter_by(id=trace_id).first()
    if not trace or trace.analysis_status != 'pending': return
    trace.analysis_status = 'analyzing'; db.commit()

    STEP 2: NLI Grounding (CPU, ~200ms)
    grounding = check_grounding(trace.generated_answer, trace.retrieved_chunks)
    grounding_rate = compute_grounding_rate(grounding)
    grounded_count = sum(1 for g in grounding if g['is_grounded'])

    STEP 3: Faithfulness (approximation = grounding_rate for free/pro)
    For enterprise + Ollama available: call Ollama LLM judge
    faithfulness = grounding_rate  # base approximation

    STEP 4: Context Precision (heuristic)
    useful_chunks = sum(1 for chunk in trace.retrieved_chunks
                       if any(chunk['text'][:100] in g['evidence_text']
                              for g in grounding if g['is_grounded']))
    context_precision = useful_chunks / len(trace.retrieved_chunks) if trace.retrieved_chunks else 0

    STEP 5: Context Recall (proxy)
    context_recall = grounding_rate  # proxy without ground truth

    STEP 6: Answer Relevance (BM25)
    from rank_bm25 import BM25Okapi
    tokenized_answer = trace.generated_answer.lower().split()
    tokenized_query = trace.query_text.lower().split()
    bm25 = BM25Okapi([tokenized_answer])
    answer_relevance = min(1.0, bm25.get_scores(tokenized_query)[0] / 10.0)

    STEP 7: Citation Quality
    citation_quality = compute_citation_quality(grounding, trace.retrieved_chunks)

    STEP 8: Failure Classification
    failure_type, failure_reason, failure_conf = classify_failure(
        faithfulness, grounding_rate, context_precision, context_recall, answer_relevance)

    STEP 9: Persist all metrics to trace record

    STEP 10: Update pipeline aggregated metrics (running avg last 100)

    STEP 11: Update chunk_stats for all retrieved chunks
    For each chunk in retrieved_chunks:
        upsert chunk_stats (increment retrieval_count)
        If chunk cited in grounding: increment citation_count
        Update citation_rate = citation_count / retrieval_count
        Set is_stale = True if citation_rate < 0.2 AND retrieval_count >= 50

    STEP 12: If failure_type is not None:
        Trigger knowledge_gap_check.delay(pipeline_id)

    STEP 13: Check monitoring alert thresholds
    If pipeline trust_score < monitoring_config.alert_trust_threshold:
        trigger alert
    """
```

---

## 10. CITATION QUALITY SCORER (`backend/app/services/citation_scorer.py`)

```python
def compute_citation_quality(
    grounding_results: list[dict],
    retrieved_chunks: list[dict],
) -> dict:
    """
    Measures citation health across 5 dimensions.

    Returns:
    {
        completeness:   float,  # fraction of sentences with a supporting chunk
        relevance:      float,  # mean confidence of grounded sentences
        overlap:        float,  # fraction of retrieved chunks actually cited
        contradictions: int,    # sentences where grounded chunk contradicts claim
        unsupported:    int     # sentences with is_grounded=False
    }

    Algorithm:
    1. completeness  = sum(is_grounded) / len(grounding_results)
    2. relevance     = mean(confidence for g in grounding_results if g['is_grounded'])
    3. cited_chunks  = {g['supporting_chunk_id'] for g if g['is_grounded']}
       overlap       = len(cited_chunks) / len(retrieved_chunks)
    4. contradictions: for each grounded sentence,
       run NLI contradiction score against its supporting chunk
       if contradiction score > entailment score: increment contradictions
    5. unsupported   = sum(1 for g if not g['is_grounded'])
    """
```

---

## 11. DOCUMENT GENERATION (`backend/app/services/doc_generator.py`)

```python
DOC_GEN_PROMPT = """
You are a technical writer. Generate a comprehensive document covering the topic: {topic}

Context: This document will be added to a knowledge base to answer user queries like:
{example_queries}

Write in clear, accurate, structured prose. Include:
- Overview / definition
- Key concepts
- Step-by-step processes where applicable
- Common edge cases
- Troubleshooting guidance

Format: {format}
Length: 600-1200 words
"""

async def generate_document_draft(
    topic: str,
    example_queries: list[str],
    format: str = "markdown",
) -> dict:
    """
    1. Build prompt from DOC_GEN_PROMPT template
    2. Call Groq API (llama-3.1-70b-versatile) with temperature=0.3
    3. If Groq unavailable: fallback to Ollama Phi-3 Mini
    4. Return { draft: str, suggested_title: str, word_count: int, format: str }
    """
```

---

## 12. RETRIEVAL SIMULATOR (`backend/app/services/retrieval_simulator.py`)

```python
SIMULATION_PROMPT = """
You are an expert RAG system architect. Given a RAG pipeline configuration, 
predict the quality metrics for a query.

Current pipeline context:
- Current Trust Score: {trust_score}
- Current embedding model: {embedding_model}
- Current chunk size: {chunk_size}
- Current retrieval strategy: {retrieval_strategy}
- Current top_k: {top_k}

Scenario to evaluate:
- chunk_size: {scenario_chunk_size}
- embedding_model: {scenario_embedding}
- retrieval_strategy: {scenario_strategy}
- top_k: {scenario_top_k}

Query: "{query}"

Based on empirical RAG research and the pipeline's historical metrics, predict:
Return ONLY valid JSON:
{
  "predicted_trust_score": float (0-100),
  "predicted_latency_ms": float,
  "predicted_cost_per_query_usd": float,
  "predicted_hallucination_rate": float (0-1),
  "confidence": float (0-1),
  "reasoning": str
}
"""
```

---

## 13. KNOWLEDGE GRAPH (`backend/app/services/knowledge_graph.py`)

```python
async def rebuild_knowledge_graph(pipeline_id: str):
    """
    Builds a document relationship graph for the pipeline.

    Algorithm:
    1. Load all documents for pipeline
    2. Embed each document title + first 500 chars with sentence-transformers
    3. Compute cosine similarity matrix between all documents
    4. Create edges where similarity > 0.5
    5. Extract topic labels via LLM:
       "Given these document titles: {titles}, group them into topic clusters.
        Return JSON: { clusters: [{label, document_ids}] }"
    6. Create knowledge_graph_nodes for each document + each topic cluster
    7. Create knowledge_graph_edges from similarity relationships
    8. Assign x/y positions using force-directed layout (networkx spring_layout)
    9. Upsert to knowledge_graph_nodes + knowledge_graph_edges tables

    Frontend renders with D3 force simulation.
    """
```

---

## 14. PRICING & PLAN GATING

```python
PLANS = {
    "free": {
        "price_inr": 0,
        "price_usd": 0,
        "traces_per_month": 1000,
        "history_days": 7,
        "grounding": True,
        "llm_judge": False,
        "auto_fix": False,
        "knowledge_graph": False,
        "benchmark": False,
        "studio": False,
        "monitoring": False,
        "investigator": False,
        "executive_dashboard": False,
        "regression": False,
        "reports": False,
        "sso": False,
        "multi_pipeline": False,   # 1 pipeline only
        "synthetic_testsets": False,
    },
    "pro": {
        "price_inr": 8200,         # ≈ $99/month
        "price_usd": 99,
        "razorpay_plan_id": "plan_pro_monthly",
        "traces_per_month": -1,    # unlimited
        "history_days": 90,
        "grounding": True,
        "llm_judge": True,
        "auto_fix": True,
        "knowledge_graph": True,
        "benchmark": True,
        "studio": True,
        "monitoring": True,
        "investigator": True,
        "executive_dashboard": False,
        "regression": True,
        "reports": True,
        "sso": False,
        "multi_pipeline": True,    # up to 5 pipelines
        "synthetic_testsets": True,
    },
    "enterprise": {
        "price_inr": 33100,        # ≈ $399/month
        "price_usd": 399,
        "razorpay_plan_id": "plan_enterprise_monthly",
        "traces_per_month": -1,
        "history_days": 365,
        "grounding": True,
        "llm_judge": True,
        "auto_fix": True,
        "auto_apply_fixes": True,  # one-click apply
        "knowledge_graph": True,
        "benchmark": True,
        "studio": True,
        "monitoring": True,
        "investigator": True,
        "executive_dashboard": True,
        "regression": True,
        "reports": True,
        "sso": True,
        "multi_pipeline": True,    # unlimited pipelines
        "synthetic_testsets": True,
        "custom_metrics": True,
        "priority_support": True,
        "cross_project_hooks": True,
        "pre_deploy_gate": True,   # CI/CD regression blocking
    },
}

# Plan gate dependency
def require_plan(minimum_plan: str):
    """FastAPI dependency: raises 403 if user plan is below minimum."""
    plan_order = {"free": 0, "pro": 1, "enterprise": 2}
    def _gate(current_user = Depends(get_current_user)):
        if plan_order[current_user.plan] < plan_order[minimum_plan]:
            raise HTTPException(
                status_code=403,
                detail=f"This feature requires the {minimum_plan} plan."
            )
        return current_user
    return _gate
```

---

## 15. REQUIREMENTS.TXT

```
# Framework
fastapi==0.111.0
uvicorn[standard]==0.29.0
pydantic==2.7.1
pydantic-settings==2.2.1
python-multipart==0.0.9

# Database
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0
alembic==1.13.1

# Cache + Task Queue
celery[redis]==5.4.0
redis==5.0.4
flower==2.0.1         # Celery monitoring

# ML / NLP
sentence-transformers==2.7.0
torch==2.3.0
scikit-learn==1.4.2   # DBSCAN for gap clustering
numpy==1.26.4
rank-bm25==0.2.2

# PDF Reports
weasyprint==61.2

# Auth
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# HTTP
httpx==0.27.0

# Payments
razorpay==1.4.1

# LLM clients
groq==0.9.0           # Groq API (document generation, investigator)
ollama==0.2.1         # Local Ollama client

# Utilities
python-dotenv==1.0.1
structlog==24.1.0     # Structured logging
```

---

## 16. DOCKER COMPOSE (`docker-compose.yml`)

```yaml
version: "3.9"

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://ri:ri@postgres:5432/raginspector
      - REDIS_URL=redis://redis:6379/0
      - GROQ_API_KEY=${GROQ_API_KEY}
      - RAZORPAY_KEY_ID=${RAZORPAY_KEY_ID}
      - RAZORPAY_KEY_SECRET=${RAZORPAY_KEY_SECRET}
      - JWT_SECRET=${JWT_SECRET}
      - OLLAMA_BASE_URL=http://ollama:11434
    depends_on:
      - postgres
      - redis
      - ollama
    volumes:
      - ./backend:/app

  worker:
    build: ./backend
    command: celery -A app.celery_app worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=postgresql+asyncpg://ri:ri@postgres:5432/raginspector
      - REDIS_URL=redis://redis:6379/0
      - GROQ_API_KEY=${GROQ_API_KEY}
      - OLLAMA_BASE_URL=http://ollama:11434
    depends_on:
      - postgres
      - redis

  beat:
    build: ./backend
    command: celery -A app.celery_app beat --loglevel=info
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=ri
      - POSTGRES_PASSWORD=ri
      - POSTGRES_DB=raginspector
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    # Pull phi3:mini on first run: docker exec raginspector-ollama-1 ollama pull phi3:mini

volumes:
  pgdata:
  ollama_data:
```

---

## 17. BUILD ORDER (Agent-Executable — 40 Steps)

```
PHASE 1 — FOUNDATION
STEP 1:  docker-compose.yml + .env.example
STEP 2:  backend/app/config.py + database.py (async SQLAlchemy)
STEP 3:  All 16 Alembic migrations (one per table, in FK order)
STEP 4:  backend/app/dependencies.py (get_current_user, require_api_key, require_plan)
STEP 5:  /api/v1/auth (register, login, JWT, API key generation)

PHASE 2 — CORE PIPELINE
STEP 6:  /api/v1/pipelines (CRUD + snapshot)
STEP 7:  /api/v1/traces/batch (ingest endpoint + rate limiting)
STEP 8:  services/grounding.py (NLI CrossEncoder — unit test with known pairs)
STEP 9:  services/failure_classifier.py (unit test all 5 rules)
STEP 10: services/trust_scorer.py (unit test with synthetic trace sets)
STEP 11: services/hallucination_cost.py
STEP 12: workers/ragas_worker.py (full RAGAS + grounding + chunk stats)
STEP 13: GET /api/v1/traces + GET /api/v1/traces/{id} (with grounding_detail)
STEP 14: GET /api/v1/metrics/dashboard

PHASE 3 — KNOWLEDGE INTELLIGENCE
STEP 15: services/knowledge_gap.py (DBSCAN clustering)
STEP 16: /api/v1/knowledge/gaps (detect + list + status update)
STEP 17: services/doc_generator.py (Groq + Ollama fallback)
STEP 18: POST /api/v1/knowledge/gaps/{id}/generate-draft
STEP 19: /api/v1/knowledge/coverage-map
STEP 20: workers/freshness_worker.py + /api/v1/knowledge/freshness

PHASE 4 — AUTO-FIX ENGINE
STEP 21: services/fix_planner.py
STEP 22: services/citation_scorer.py
STEP 23: /api/v1/autofix (recommendations + apply + dismiss)

PHASE 5 — BILLING
STEP 24: /api/v1/billing (Razorpay subscription + webhook + plan gate)

PHASE 6 — SDK
STEP 25: sdk/raginspector/tracer.py (decorator + context manager)
STEP 26: sdk/raginspector/async_tracer.py
STEP 27: sdk/raginspector/integrations/langchain.py
STEP 28: sdk/raginspector/integrations/llamaindex.py
STEP 29: sdk/raginspector/integrations/haystack.py
STEP 30: sdk/setup.py + README

PHASE 7 — ADVANCED FEATURES
STEP 31: /api/v1/benchmark (retrieval + LLM comparison + workers)
STEP 32: /api/v1/studio (chunk optimizer + retrieval simulator + prompt analyzer)
STEP 33: services/knowledge_graph.py + /api/v1/knowledge/graph
STEP 34: /api/v1/monitoring (config + worker/beat + history)
STEP 35: /api/v1/regression (snapshots + compare + pre-deploy-check)
STEP 36: /api/v1/testsets (synthetic test set generator + runner)
STEP 37: services/ai_investigator.py + /api/v1/investigator/query
STEP 38: /api/v1/metrics/executive + /api/v1/reports
STEP 39: /api/v1/integrations (cross-project webhook hooks)

PHASE 8 — FRONTEND
STEP 40: Next.js 14 frontend — implement all pages in this order:
  40a. layout.tsx (sidebar, nav, auth wrapper)
  40b. /dashboard (Trust Score gauge, Hallucination Cost, Failure Pie, Trend Chart)
  40c. /traces + /traces/[id] (sentence-level grounding visualization — HERO FEATURE)
  40d. /failures (failure summary + patterns)
  40e. /knowledge/map + /knowledge/gaps + /knowledge/freshness
  40f. /autofix (Fix Planner cards with effort + trust improvement estimates)
  40g. /studio/chunks + /studio/simulator + /studio/prompts
  40h. /benchmark/retrieval + /benchmark/models
  40i. /knowledge/graph (D3 force-directed visualization)
  40j. /monitoring
  40k. /investigator (AI chat interface)
  40l. /executive (enterprise-only)
  40m. /settings/pipeline + /settings/billing

INTEGRATION TEST (after STEP 40):
  - Install SDK: pip install -e ./sdk
  - Run demo LangChain RAG pipeline with RAGInspectorCallback
  - Verify: traces captured → analyzed → Trust Score updated → gaps detected → recommendations generated
  - Verify: billing flow end-to-end (Razorpay test mode)
  - Verify: monitoring probe runs on schedule
```

---

## 18. CROSS-PROJECT INTEGRATION HOOKS

These are enterprise-tier webhooks that fire lifecycle events to other RAGInspector portfolio tools:

```python
INTEGRATION_EVENTS = {
    "trust_score_drop": {
        "target": "agent_audit",
        "payload": {
            "event": "rag_trust_degraded",
            "pipeline_id": str,
            "trust_score": float,
            "delta": float,
            "recommendation": "Increase agent risk threshold until RAG quality is restored"
        }
    },
    "regression_detected": {
        "target": "ghost_eval",
        "payload": {
            "event": "rag_regression_block",
            "pipeline_id": str,
            "baseline_trust": float,
            "current_trust": float,
            "severity": str,
            "recommendation": "Block LLM deployment until RAG quality is restored"
        }
    },
    "high_latency_detected": {
        "target": "inference_forge",
        "payload": {
            "event": "rag_retrieval_cost_spike",
            "pipeline_id": str,
            "retrieval_latency_ms": float,
            "recommendation": "Review vector store infrastructure and caching"
        }
    },
    "trust_drop_with_drift": {
        "target": "embedding_drift",
        "payload": {
            "event": "rag_trust_correlates_with_drift",
            "pipeline_id": str,
            "embedding_model": str,
            "recommendation": "Check vector health to explain Trust Score degradation"
        }
    },
    "sensitive_doc_indexed": {
        "target": "privacy_lens",
        "payload": {
            "event": "rag_sensitive_content_alert",
            "pipeline_id": str,
            "document_id": str,
            "recommendation": "Review document before indexing into knowledge base"
        }
    }
}
```

---

## 19. POSITIONING SUMMARY

**Sell:** Enterprise AI Knowledge Reliability Platform

**Not:** RAG observability tool

**Core message:** "We continuously improve the quality and reliability of your organization's AI knowledge."

**The loop that competitors don't close:**

```
Detect failure
    ↓
Root-cause it (retrieval_miss / context_miss / hallucination)
    ↓
Quantify business cost ($USD/month)
    ↓
Recommend the fix (with effort + trust improvement estimate)
    ↓
Generate the fix (document drafts, chunk removal, config changes)
    ↓
Verify improvement (pre/post Trust Score comparison)
    ↓
Prevent regression (CI/CD gate before next deploy)
```

**The metrics that sell to executives:**
- Trust Score: 91/100
- Hallucination Cost: $2,340/month
- Knowledge Coverage: 78%
- Revenue at Risk: $11,700/month

**The differentiators that win hiring conversations:**
- Sentence-level NLI grounding attribution
- Knowledge graph built from chunk relationships
- AI Investigator: natural language query over metrics
- Pre-deploy regression gate integrated with CI/CD
- Cross-portfolio integration hooks (AgentAudit, GhostEval, InferenceForge)
```
