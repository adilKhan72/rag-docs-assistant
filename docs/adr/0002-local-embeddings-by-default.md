# ADR-0002: Local embeddings by default, behind an interface

**Status:** Accepted

## Context
Embedding every chunk with a hosted API costs money, sends document text to a third party and needs a key just
to run the tests. Retrieval quality must still be measurable in CI.

## Decision
An `Embedder` interface with a default local implementation (`fastembed`, ONNX, `BAAI/bge-small-en-v1.5`,
384 dimensions, no GPU, no PyTorch). A hosted embedder (e.g. OpenAI) can be configured instead. The embedding model
name and dimension are stored with every chunk.

## Consequences
- CI runs the real retrieval pipeline and the real eval with no keys.
- Switching models means re-embedding. Storing the model name per chunk makes mixed-model indexes detectable,
  and queries refuse to mix them.
- A small local model is not state of the art. The eval set (ADR-0004) is how a better model would justify its cost.
