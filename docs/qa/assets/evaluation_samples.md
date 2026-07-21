# Sample evaluation set (ground truth)

Lightweight pairs for manual / interview verification of ingest + analysis.

| id | query | expected_failure | notes |
|----|-------|------------------|-------|
| ev-01 | What is the refund window for annual plans? | none | Answer must stay within 14-day policy |
| ev-02 | Does the API support streaming responses? | hallucination | Context says streaming not available |
| ev-03 | How do I rotate API keys? | retrieval_miss / coverage_gap | Needs api_key_rotation.md ingested |
| ev-04 | What SLA do enterprise customers get? | coverage_gap | Needs enterprise_sla.md |

Prompts for studio: see `payloads/studio_prompt.json`.
