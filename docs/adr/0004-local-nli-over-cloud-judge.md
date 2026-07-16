# ADR 0004: Local NLI grounding over cloud-only judges

- **Status:** Accepted  
- **Date:** 2026-07

## Context

Need sentence-level groundedness without requiring paid LLM APIs for every analysis in CI and demos.

## Decision

Default to **local** cross-encoder / NLI models via sentence-transformers in the analysis worker. Optional HF / Ollama paths for richer RAGAS-style metrics when configured.

## Alternatives considered

| Option | Why not default |
|--------|-----------------|
| GPT/Claude as sole judge | Cost, rate limits, nondeterminism in CI |
| Pure embedding cosine | Weak for contradiction / faithfulness |
| Skip grounding in v1 | Kills the product differentiator |

## Consequences

- Cold start and RAM matter; document worker sizing.  
- Heuristic fallbacks when models fail to load.  
- Hiring signal: real ML in the loop, not only API wrappers.
