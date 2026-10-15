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
