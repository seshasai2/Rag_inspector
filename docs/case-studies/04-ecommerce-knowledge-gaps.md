# Case study: Ecommerce knowledge gaps

## Business

**Harbor & Co.** runs a commerce RAG assistant for shipping, returns, and product care. Catalog changes weekly; help-center articles lag.

## Problem

High “I don’t know” handoffs and invented SKU compatibility claims. Support leaders suspected **coverage gaps** — questions with no adequate chunk — but analytics only showed generic thumbs-down rates (**14%** negative).

## Architecture

- SaaS RAGInspector project connected to production instrumented bot
- Knowledge-gap service clustered low-confidence / low-recall queries
- Chunk quality heatmap for over-retrieved but under-cited FAQs
- Weekly executive report emailed to CX + content ops

## Implementation

1. Enabled knowledge gap views (`/knowledge/gaps`) fed by low context recall and `coverage_gap` failure class.
2. Content team prioritized writing articles for top gap clusters (gift cards, international duties, mattress trials).
3. Re-ingested updated articles; watched citation_rate on related chunks climb.
4. BM25 metrics highlighted brand/SKU token queries where lexical match beat embeddings (**37%** win rate) → added hybrid search in storefront bot.
5. Autofix recommendations suggested chunk merges for fragmented care instructions.

## Results

| Metric | Week 0 | Week 8 |
|--------|--------|--------|
| Negative feedback rate | 14% | 7.6% |
| `coverage_gap` share of failures | 28% | 11% |
| Mean context recall | 0.58 | 0.74 |
| New articles shipped from gap report | — | 23 |

## ROI

- Deflected estimated **1,900** support chats / month at $3.80 fully loaded → **~$7,200** / month.
- Content ops spent ~40 hours writing articles; first-month net positive.

## Performance

Dashboard cache TTL kept CX leadership page p95 at **65 ms**. Gap aggregation job (beat) completed in **< 90 s** nightly over ~1.2M traces retained 30 days.

## Lessons learned

1. Knowledge gaps convert RAG observability into a content backlog — different buyer than ML eng.
2. Failure type mix matters more than a single faithfulness number for CX.
3. Hybrid retrieval is disproportionate for SKU and policy keyword questions.
4. Keep executive reports short: top 10 gaps beat full CSV dumps.
