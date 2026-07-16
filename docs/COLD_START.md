# ML cold start & model cache (Phase 6.3)

RAGInspector analysis uses two local `sentence-transformers` models:

| Role | Default Hugging Face id | Used by |
|------|-------------------------|---------|
| Embeddings | `all-MiniLM-L6-v2` (`EMBEDDING_MODEL_NAME`) | RAGAS-style metrics, context recall, fix-recommendation clustering |
| NLI cross-encoder | `cross-encoder/nli-deberta-v3-small` (`NLI_MODEL_NAME`) | Answer grounding / hallucination sentences |

Canonical loader: `app/services/ml_models.py`.

## Lazy load (default path)

Models are **not** imported at API process start. The first call to:

- `get_embedding_model()` or
- `get_nli_cross_encoder()`

downloads (if missing from HF cache) and loads weights into **that process**. Subsequent calls reuse the in-process singleton (thread-safe).

If load fails, analysis continues with keyword / lexical fallbacks (grounding still returns results; quality is lower).

## Warm cache (Celery workers)

Each Celery **worker child process** runs `warm_ml_models()` on `worker_process_init` when:

```bash
WARM_ML_MODELS_ON_WORKER_START=true   # default
```

That shifts cold start from the first user trace to worker boot.

Disable for tiny local machines or CI workers that never analyze:

```bash
WARM_ML_MODELS_ON_WORKER_START=false
```

Manual warm (same process):

```python
from app.services.ml_models import warm_ml_models, model_cache_status
warm_ml_models()
print(model_cache_status())
```

## Cold-start expectations

| Event | Typical cost |
|-------|----------------|
| First download of both models | Minutes + disk (HF hub); ensure outbound HTTPS or pre-cache volumes |
| First load from local HF cache (CPU) | Often **tens of seconds** per model on small hosts |
| After warm / after first lazy load | Inference only (ms–s per trace depending on chunk count) |

**API containers** do not warm models by default (ingest is lightweight). Only analysis workers need the cache.

**Prefork workers:** each child has its own memory copy — budget RAM ≈ (embedding + NLI) × concurrency.

## Ops checklist

1. Pre-pull models into the image or a shared HF cache volume in production.
2. Keep `WARM_ML_MODELS_ON_WORKER_START=true` on analysis workers.
3. Watch worker logs for `Loading … (lazy)` vs `ML model cache warm complete`.
4. If first traces show keyword-only grounding, check OOM / missing torch / HF rate limits.

## Related

- Deployment: `docs/DEPLOYMENT.md`
- Config: `.env.example` (`EMBEDDING_MODEL_NAME`, `NLI_MODEL_NAME`, `WARM_ML_MODELS_ON_WORKER_START`)
