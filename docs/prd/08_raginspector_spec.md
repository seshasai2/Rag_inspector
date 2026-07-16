# RAGInspector — Agent Build Specification v2.0
**Classification:** Enterprise SaaS | Production RAG Pipeline Observability  
**Stack:** FastAPI · Next.js 14 · PostgreSQL · Redis · Celery · sentence-transformers · Razorpay  
**GPU requirement:** GTX 1650 for Ollama Phi-3 mini Q4 (LLM-as-judge). CPU handles NLI grounding.

---

## AGENT INSTRUCTIONS
Build in exact sequence in BUILD ORDER. RAGInspector's core mechanic is a Python SDK that instruments RAG pipelines without code changes. The dashboard must show sentence-level grounding attribution. The Trust Score (0-100) and Hallucination Cost ($/month) are the two hero metrics.

---

## 1. OVERVIEW
RAGInspector instruments every step of a RAG pipeline — query embedding, vector retrieval, context assembly, LLM generation — and computes RAGAS metrics, grounding verification (NLI), and failure classification. Every failed query is classified by root cause: retrieval_miss, context_miss, or hallucination.

**Hero metrics:**
- Trust Score: 91/100
- Hallucination Cost: $2,340/month estimated business impact

---

## 2. PROJECT STRUCTURE
```
raginspector/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/v1/
│   │   │   ├── auth.py
│   │   │   ├── traces.py        # Query trace CRUD
│   │   │   ├── pipelines.py     # Pipeline configuration
│   │   │   ├── metrics.py       # RAGAS + trust metrics
│   │   │   ├── failures.py      # Failure classification
│   │   │   ├── knowledge.py     # Missing knowledge detection
│   │   │   ├── autofix.py       # Auto-fix engine
│   │   │   └── reports.py
│   │   ├── workers/
│   │   │   ├── ragas_worker.py  # Async RAGAS computation
│   │   │   └── grounding_worker.py
│   │   ├── services/
│   │   │   ├── grounding.py     # NLI grounding check (CPU)
│   │   │   ├── bm25_service.py  # BM25 comparison
│   │   │   ├── trust_scorer.py  # Trust Score computation
│   │   │   ├── failure_classifier.py
│   │   │   └── hallucination_cost.py
│   ├── alembic/
│   └── requirements.txt
├── sdk/
│   ├── raginspector/
│   │   ├── __init__.py
│   │   ├── tracer.py            # Core tracing decorators
│   │   ├── integrations/
│   │   │   ├── langchain.py     # LangChain callback
│   │   │   ├── llamaindex.py    # LlamaIndex callback
│   │   │   └── haystack.py      # Haystack component
│   │   └── client.py
│   └── setup.py
├── frontend/
│   └── src/app/
│       ├── dashboard/page.tsx
│       ├── traces/page.tsx
│       ├── traces/[id]/page.tsx  # Sentence-level grounding view
│       ├── failures/page.tsx
│       └── autofix/page.tsx
└── docker-compose.yml
```

---

## 3. DATABASE SCHEMA

### 3.1 users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    plan VARCHAR(50) DEFAULT 'free',
    api_key VARCHAR(255) UNIQUE,
    razorpay_customer_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.2 pipelines
```sql
CREATE TABLE pipelines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    framework VARCHAR(100),               -- langchain, llamaindex, haystack, custom
    description TEXT,
    -- Business context for cost calculation
    queries_per_month INTEGER DEFAULT 10000,
    cost_per_wrong_answer_usd FLOAT DEFAULT 5.0,
    -- Aggregated metrics (updated incrementally)
    trust_score FLOAT,
    total_traces INTEGER DEFAULT 0,
    hallucination_rate FLOAT DEFAULT 0.0,
    faithfulness_avg FLOAT,
    context_precision_avg FLOAT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_trace_at TIMESTAMPTZ
);
```

### 3.3 query_traces
```sql
CREATE TABLE query_traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID REFERENCES pipelines(id) ON DELETE CASCADE,
    -- Query
    query_text TEXT NOT NULL,
    query_embedding FLOAT[],             -- stored for BM25 comparison
    -- Retrieved chunks
    retrieved_chunks JSONB NOT NULL,     -- list of { chunk_id, text, score, rank }
    n_chunks_retrieved INTEGER,
    -- Generation
    generated_answer TEXT NOT NULL,
    llm_model VARCHAR(255),
    -- RAGAS metrics
    faithfulness FLOAT,                   -- fraction of answer claims grounded in context
    context_precision FLOAT,              -- fraction of retrieved chunks that are useful
    context_recall FLOAT,                 -- fraction of needed info that was retrieved
    answer_relevance FLOAT,               -- is answer relevant to query
    -- Grounding
    grounding_results JSONB,             -- list of { sentence, is_grounded, supporting_chunk_id }
    grounded_sentence_count INTEGER,
    total_sentence_count INTEGER,
    grounding_rate FLOAT,                 -- grounded_sentence_count / total_sentence_count
    -- Classification
    failure_type VARCHAR(100),            -- retrieval_miss | context_miss | hallucination | none
    failure_reason TEXT,
    -- Timing
    total_latency_ms FLOAT,
    retrieval_latency_ms FLOAT,
    generation_latency_ms FLOAT,
    -- Status
    analysis_status VARCHAR(50) DEFAULT 'pending'
        CHECK (analysis_status IN ('pending', 'analyzing', 'complete', 'failed')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_traces_pipeline ON query_traces(pipeline_id, created_at DESC);
CREATE INDEX idx_traces_failure ON query_traces(pipeline_id, failure_type);
CREATE INDEX idx_traces_status ON query_traces(analysis_status);
```

### 3.4 chunk_stats
```sql
CREATE TABLE chunk_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID REFERENCES pipelines(id),
    chunk_id VARCHAR(500) NOT NULL,       -- identifier from vector store
    chunk_text TEXT,
    -- Usage statistics
    retrieval_count INTEGER DEFAULT 0,
    citation_count INTEGER DEFAULT 0,     -- times chunk contributed to grounded answer
    citation_rate FLOAT,                  -- citation_count / retrieval_count
    -- Health
    last_retrieved_at TIMESTAMPTZ,
    is_stale BOOLEAN DEFAULT false,       -- citation_rate < 0.2 after 50+ retrievals
    UNIQUE(pipeline_id, chunk_id)
);
```

### 3.5 missing_knowledge_alerts
```sql
CREATE TABLE missing_knowledge_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID REFERENCES pipelines(id),
    query_cluster_label VARCHAR(500),     -- representative query from cluster
    query_count INTEGER DEFAULT 1,
    failure_rate FLOAT,
    suggested_document_topic TEXT,        -- "Add documentation about: OAuth Refresh Tokens"
    auto_fix_draft TEXT,                  -- AI-generated document draft
    status VARCHAR(50) DEFAULT 'open'
        CHECK (status IN ('open', 'acknowledged', 'fixed')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 4. SDK (`sdk/raginspector/tracer.py`)

```python
import functools
import time
import threading
import queue
import httpx

class RAGTracer:
    """
    Usage:
        from raginspector import RAGTracer
        
        tracer = RAGTracer(api_key="ri_xxxxx", pipeline_id="uuid")
        
        @tracer.trace_retrieval
        def retrieve(query: str) -> list[dict]:
            ...  # returns list of {chunk_id, text, score}
        
        @tracer.trace_generation
        def generate(query: str, context: list[str]) -> str:
            ...  # returns answer string
    """
    def __init__(self, api_key: str, pipeline_id: str, 
                 api_url: str = "https://api.raginspector.com"):
        self.api_key = api_key
        self.pipeline_id = pipeline_id
        self.api_url = api_url
        self._current_trace: dict | None = None
        self._queue = queue.Queue()
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
    
    def trace_retrieval(self, func):
        """Decorator for retrieval function"""
        @functools.wraps(func)
        def wrapper(query: str, *args, **kwargs):
            start = time.monotonic()
            result = func(query, *args, **kwargs)
            retrieval_latency = (time.monotonic() - start) * 1000
            
            self._current_trace = {
                "query_text": query,
                "retrieved_chunks": result if isinstance(result, list) else [],
                "retrieval_latency_ms": retrieval_latency
            }
            return result
        return wrapper
    
    def trace_generation(self, func):
        """Decorator for generation function"""
        @functools.wraps(func)
        def wrapper(query: str, context, *args, **kwargs):
            start = time.monotonic()
            result = func(query, context, *args, **kwargs)
            generation_latency = (time.monotonic() - start) * 1000
            
            if self._current_trace:
                trace = {
                    **self._current_trace,
                    "generated_answer": result if isinstance(result, str) else str(result),
                    "generation_latency_ms": generation_latency,
                    "total_latency_ms": self._current_trace.get("retrieval_latency_ms", 0) + generation_latency,
                    "pipeline_id": self.pipeline_id
                }
                self._queue.put(trace)
                self._current_trace = None
            return result
        return wrapper
    
    def _flush_loop(self):
        while True:
            time.sleep(1)
            batch = []
            try:
                while True:
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
                timeout=10.0
            )
        except Exception:
            pass
```

### 4.1 LangChain Integration (`sdk/raginspector/integrations/langchain.py`)
```python
from langchain_core.callbacks import BaseCallbackHandler

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
        self._pending_trace = {}
    
    def on_retriever_end(self, documents, **kwargs):
        self._pending_trace["retrieved_chunks"] = [
            {"chunk_id": doc.metadata.get("id", f"chunk_{i}"), 
             "text": doc.page_content, 
             "score": doc.metadata.get("score", 0.0),
             "rank": i}
            for i, doc in enumerate(documents)
        ]
    
    def on_chain_end(self, outputs, **kwargs):
        if "retrieved_chunks" in self._pending_trace:
            trace = {
                **self._pending_trace,
                "generated_answer": str(outputs.get("result", "")),
                "pipeline_id": self.tracer.pipeline_id
            }
            self.tracer._queue.put(trace)
            self._pending_trace = {}
```

---

## 5. API ROUTES

### 5.1 Traces
```
POST /api/v1/traces/batch
  Headers: X-API-Key
  Body: { traces: list[TraceInput] }
  Response: { accepted: int, queued_for_analysis: int }
  Logic: store traces, dispatch Celery tasks for RAGAS analysis

GET /api/v1/traces
  Auth: required
  Query: pipeline_id, failure_type?, start_date?, end_date?, limit=50, offset=0
  Response: { traces: list[TraceSummary], total: int }

GET /api/v1/traces/{trace_id}
  Auth: required
  Response: full trace with grounding_results expanded:
  {
    ...trace fields,
    grounding_detail: list[{
      sentence: str,
      is_grounded: bool,
      supporting_chunk: { chunk_id, text, similarity_score } | null,
      confidence: float
    }]
  }
```

### 5.2 Metrics
```
GET /api/v1/metrics/dashboard
  Auth: required
  Query: pipeline_id
  Response: {
    trust_score: float,           -- 0-100 composite
    hallucination_cost_usd: float, -- monthly estimate
    faithfulness_avg: float,
    context_precision_avg: float,
    context_recall_avg: float,
    failure_breakdown: {
      retrieval_miss_pct: float,   -- % of failures from bad retrieval
      context_miss_pct: float,     -- % from context not containing answer
      hallucination_pct: float     -- % from LLM hallucinating
    },
    trend_7d: list[{ date, trust_score, faithfulness, failure_rate }],
    top_failing_queries: list[{ query, failure_type, count }]
  }

GET /api/v1/metrics/chunks
  Auth: required
  Query: pipeline_id, is_stale?=false
  Response: { chunks: list[ChunkStats], stale_count: int }
```

### 5.3 Failures
```
GET /api/v1/failures/summary
  Auth: required
  Query: pipeline_id, days=7
  Response: {
    total_failures: int,
    by_type: { retrieval_miss: int, context_miss: int, hallucination: int },
    most_common_failure_patterns: list[{ pattern, count, example_query }]
  }
```

### 5.4 Missing Knowledge
```
GET /api/v1/knowledge/gaps
  Auth: required
  Query: pipeline_id
  Response: {
    gaps: list[{
      topic, query_count, failure_rate, suggested_document_topic, auto_fix_draft
    }]
  }
  Logic: cluster failed queries by topic, identify missing coverage

POST /api/v1/knowledge/gaps/{gap_id}/generate-draft
  Auth: required (pro+)
  Response: {
    draft: str,       -- AI-generated document about the missing topic
    suggested_title: str,
    word_count: int
  }
  Logic: call Ollama/Groq API to generate a document covering the gap topic
```

### 5.5 Auto-Fix
```
GET /api/v1/autofix/recommendations
  Auth: required (pro+)
  Query: pipeline_id
  Response: {
    recommendations: list[{
      type: "add_document" | "remove_stale_chunk" | "update_embedding_model" | "tune_retrieval",
      priority: "critical" | "high" | "medium",
      description: str,
      estimated_impact: str,
      action: { type, parameters }
    }]
  }
  Level 4 feature: this is what turns RAGInspector into a revenue product

POST /api/v1/autofix/apply/{recommendation_id}
  Auth: required (enterprise)
  Response: { applied: bool, result: str }
```

---

## 6. SERVICES

### 6.1 Grounding Service (`backend/app/services/grounding.py`)
```python
from sentence_transformers import CrossEncoder

_nli_model = None

def get_nli_model():
    global _nli_model
    if _nli_model is None:
        # 85MB model, runs on CPU < 100ms per pair
        _nli_model = CrossEncoder('cross-encoder/nli-deberta-v3-small')
    return _nli_model

def check_grounding(answer: str, chunks: list[dict]) -> list[dict]:
    """
    For each sentence in answer, check if it is entailed by at least one chunk.
    
    Algorithm:
    1. Split answer into sentences using simple sentence splitter:
       sentences = [s.strip() for s in re.split(r'[.!?]+', answer) if s.strip()]
    
    2. For each sentence:
       a. Run NLI against each chunk text:
          scores = nli_model.predict([(chunk_text, sentence) for chunk in chunks])
          # scores shape: [n_chunks, 3] — [contradiction, neutral, entailment]
       b. entailment_scores = scores[:, 2]  -- take entailment column
       c. best_chunk_idx = argmax(entailment_scores)
       d. best_score = entailment_scores[best_chunk_idx]
       e. is_grounded = best_score > 0.5  -- entailment threshold
    
    3. Return: list of {
        sentence: str,
        is_grounded: bool,
        supporting_chunk_id: str | null,
        confidence: float
       }
    
    Batch for efficiency: process all (chunk, sentence) pairs in one model.predict() call
    """

def compute_grounding_rate(grounding_results: list[dict]) -> float:
    if not grounding_results:
        return 0.0
    return sum(1 for r in grounding_results if r["is_grounded"]) / len(grounding_results)
```

### 6.2 Failure Classifier (`backend/app/services/failure_classifier.py`)
```python
def classify_failure(trace: QueryTrace) -> tuple[str | None, str]:
    """
    Classify failure type based on metrics.
    
    Rules (in order):
    1. If faithfulness < 0.5 AND grounding_rate < 0.5:
       → "hallucination"
       → reason: "Answer contains ungrounded claims not supported by retrieved context"
    
    2. If context_precision < 0.3 (most chunks irrelevant):
       → "retrieval_miss"
       → reason: "Retrieval returned mostly irrelevant chunks"
    
    3. If context_recall < 0.4 (needed info not retrieved):
       → "retrieval_miss"
       → reason: "Retrieval failed to surface relevant documents"
    
    4. If faithfulness > 0.7 but answer_relevance < 0.5:
       → "context_miss"
       → reason: "Retrieved context does not contain information needed to answer"
    
    5. If all metrics > 0.7:
       → None (no failure)
       → reason: ""
    
    Default: → "context_miss"
    """
```

### 6.3 Trust Scorer (`backend/app/services/trust_scorer.py`)
```python
def compute_trust_score(recent_traces: list[QueryTrace]) -> float:
    """
    Composite score 0-100 from recent 100 traces:
    
    faithfulness_component = mean(faithfulness) * 30
    grounding_component = mean(grounding_rate) * 30
    retrieval_component = mean(context_precision) * 20
    reliability_component = (1 - failure_rate) * 20
    
    trust_score = faithfulness_component + grounding_component +
                  retrieval_component + reliability_component
    
    Return round(trust_score, 1)
    """
```

### 6.4 Hallucination Cost (`backend/app/services/hallucination_cost.py`)
```python
def estimate_hallucination_cost(pipeline: Pipeline, recent_traces: list) -> float:
    """
    hallucination_rate = count(failure_type="hallucination") / len(recent_traces)
    monthly_hallucinations = pipeline.queries_per_month * hallucination_rate
    monthly_cost = monthly_hallucinations * pipeline.cost_per_wrong_answer_usd
    
    Return monthly_cost
    """
```

---

## 7. RAGAS WORKER (`backend/app/workers/ragas_worker.py`)
```python
@celery_app.task(name="compute_ragas")
def compute_ragas_task(trace_id: str):
    """
    1. Fetch trace from DB
    2. Compute grounding with NLI model (CPU):
       grounding_results = check_grounding(trace.generated_answer, trace.retrieved_chunks)
    3. Compute faithfulness:
       faithfulness = grounding_rate (approximation without LLM judge for speed)
       For pro+ plans: use Ollama LLM-as-judge (runs async, does not block)
    4. Compute context_precision:
       Heuristic: fraction of retrieved chunks whose text appears in answer
       (simplified — full RAGAS requires LLM judge)
    5. Classify failure type
    6. Update trace record
    7. Update pipeline aggregated metrics (running average)
    8. Update chunk_stats (increment retrieval_count, citation_count)
    """
```

---

## 8. FRONTEND

### Trace Detail (`/traces/[id]`)
```
GROUNDING VISUALIZATION (hero element):
  Answer text displayed with sentence-level color coding:
    Green: is_grounded = true
    Red: is_grounded = false
    Hover sentence → highlight supporting chunk on right
  
  RIGHT PANEL: Retrieved Chunks
    Each chunk as a card
    Highlighted: if it supports a currently-hovered sentence
    Show: chunk_id, score, text excerpt

METRICS ROW:
  Faithfulness: 0.91 | Context Precision: 0.74 | Grounding Rate: 87%

FAILURE CLASSIFICATION:
  Green banner: "✓ No Failure Detected" OR
  Red banner: "✗ Retrieval Miss — Query: 'OAuth token refresh' not covered in knowledge base"
```

### Dashboard (`/dashboard`)
```
TRUST SCORE GAUGE (hero):
  Large circular gauge showing 91/100
  Color: green > 80, amber 60-80, red < 60

HALLUCINATION COST CARD:
  "$2,340/month" in large red text
  "Based on 4.2% hallucination rate × 10,000 queries/month × $5.00/wrong answer"
  Editable: click to change cost_per_wrong_answer

FAILURE PIE CHART:
  Recharts PieChart: Retrieval Miss (61%) | Context Miss (23%) | Hallucination (16%)

TREND CHART:
  Trust score + faithfulness over last 30 days
```

### Auto-Fix Page (`/autofix`)
```
RECOMMENDATIONS LIST:
  Priority-sorted cards:
  
  🔴 CRITICAL: Add document "OAuth Refresh Token Flow"
    "47 queries failed in last 7 days with no relevant retrieval"
    [Generate Draft] [Mark Fixed]
  
  🟡 HIGH: Remove 8 stale chunks (citation rate < 5%)
    "These chunks are retrieved but never cited in grounded answers"
    [Preview] [Remove All]
  
  📊 MEDIUM: Consider re-embedding with text-embedding-3-small
    "Current model shows 23% coverage gap on technical queries"
    [Learn More]
```

---

## 9. PRICING
```python
PLANS = {
    "free":       { "traces_per_month": 1000, "history_days": 7, "grounding": True, "llm_judge": False },
    "pro":        { "price_usd": 99, "traces_per_month": -1, "history_days": 90, "llm_judge": True, "auto_fix": True },
    "enterprise": { "price_usd": 399, "traces_per_month": -1, "sso": True, "custom_metrics": True, "auto_apply_fixes": True }
}
```

---

## 10. REQUIREMENTS.TXT
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0
alembic==1.13.1
pydantic==2.7.1
celery[redis]==5.4.0
redis==5.0.4
sentence-transformers==2.7.0
torch==2.3.0
rank-bm25==0.2.2
razorpay==1.4.1
weasyprint==61.2
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
numpy==1.26.4
httpx==0.27.0
```

---

## 11. BUILD ORDER
```
STEP 1:  Database + migrations
STEP 2:  Auth + API key generation
STEP 3:  Pipeline CRUD
STEP 4:  Trace batch ingestion endpoint
STEP 5:  NLI grounding service (unit test with known entailment pairs)
STEP 6:  Failure classifier (unit test all 4 rules)
STEP 7:  Trust scorer (unit test with synthetic traces)
STEP 8:  Hallucination cost estimator
STEP 9:  RAGAS worker (Celery async analysis)
STEP 10: Chunk stats tracking
STEP 11: Missing knowledge gap detector
STEP 12: Auto-fix recommendation engine
STEP 13: Document draft generator (Ollama/Groq)
STEP 14: Razorpay billing + plan gating
STEP 15: SDK: RAGTracer decorator
STEP 16: SDK: LangChain callback
STEP 17: Frontend dashboard (Trust Score gauge + Hallucination Cost)
STEP 18: Frontend trace detail (sentence-level grounding visualization)
STEP 19: Frontend auto-fix page
STEP 20: Docker Compose
STEP 21: Integration test: run demo RAG pipeline, verify traces captured + analyzed
```
