# ADR-0004: Retrieval evals gate CI. Answer evals are separate and opt-in

**Status:** Accepted

## Context
Prompt, chunking and ranking changes regress quality silently. Unit tests don't catch "the right passage is no
longer in the top 5".

## Decision
- A versioned golden set (`evals/golden.jsonl`): questions over the bundled sample corpus, each labelled with the
  chunk(s) that answer it, plus unanswerable questions that should be abstained on.
- **Retrieval eval** (deterministic, no LLM): recall@5 and MRR for vector-only, keyword-only and hybrid. Runs in
  CI and **fails the build** below committed thresholds, so a regression can't merge silently.
- **Answer eval** (needs a real model): LLM-judged faithfulness and answer relevance, plus abstention accuracy on the
  unanswerable set. Run on demand. Results are committed as reports, not used as a CI gate, because they cost money and vary between runs.

## Consequences
- The CI gate is cheap, stable and meaningful. It measures the part of RAG that most often breaks.
- Thresholds are set from measured baselines, and raising them is a deliberate commit.
