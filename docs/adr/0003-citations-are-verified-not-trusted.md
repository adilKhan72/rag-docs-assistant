# ADR-0003: Citations are verified, not trusted, and the system says "I don't know"

**Status:** Accepted

## Context
The main failure of RAG systems is a fluent answer that the retrieved context doesn't support. Asking the model
to cite sources helps, but models also invent citations.

## Decision
- Retrieved chunks are numbered `[1]..[n]` in the prompt, and the model returns structured output: answer text plus the
  list of chunk numbers it relied on.
- The service **verifies** every citation refers to a chunk that was actually retrieved, and that the answer cites
  at least one. Otherwise the answer is rejected (one corrective retry, then "I don't know").
- If retrieval evidence is weak (top fused score below a threshold tuned on the eval set), the model isn't called:
  the response is "I don't know", with the closest sources listed.
- Document text is untrusted input. The prompt tells the model to ignore instructions inside documents.

## Consequences
- Some answerable questions get "I don't know". For a docs assistant, a wrong answer costs more than an abstention.
- Citation verification checks structure, not truth. Faithfulness is measured separately by the answer evals (ADR-0004).

## Calibration (milestone 3)
`python -m evals.calibrate_abstain` measured best-hit cosine similarity with `bge-small-en-v1.5` on the golden set:

| | min | median | max |
|---|---|---|---|
| answerable (35) | 0.640 | 0.788 | 0.927 |
| unanswerable (6) | 0.517 | 0.610 | 0.655 |

The distributions overlap (0.640–0.655), so no single threshold separates them, and a "best" threshold fitted to
41 questions would overfit. The design therefore has **two stages**:
1. **Retrieval pre-filter at 0.62.** On this set it never blocks an answerable question and stops 4 of 6 unanswerable
   ones before any model call (cheap and fast).
2. **The model's own judgement** for the ambiguous band: it must return `answerable: false` when the passages don't
   contain the answer. That is measured by the answer eval, not assumed.
