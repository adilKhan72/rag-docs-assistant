# rag-docs-assistant

Retrieval-augmented question answering over a document collection, built the way I'd put RAG into production:
**hybrid retrieval, answers that cite their sources (and are checked for it), and evals that gate every pull request.**

```mermaid
flowchart LR
    subgraph Ingest
        D[Markdown / text docs] --> S[LangChain splitter<br/>heading-aware chunks]
        S --> E[Embeddings<br/>local fastembed by default]
        E --> PG[(PostgreSQL<br/>pgvector + tsvector)]
    end
    subgraph Query
        Q[Question] --> V[Vector search<br/>cosine, HNSW]
        Q --> K[Keyword search<br/>Postgres full-text]
        V --> F[Reciprocal Rank Fusion]
        K --> F
        F --> G{Enough evidence?}
        G -- no --> N[“I don't know” + closest sources]
        G -- yes --> L[LLM answer with [n] citations]
        L --> C[Citation check:<br/>every claim cites a retrieved chunk]
    end
    PG --- V & K
    MCP[MCP server<br/>search_docs / ask] --> Q
```

| | |
|---|---|
| **API** | FastAPI: `POST /ingest`, `POST /search`, `POST /ask` |
| **Store** | PostgreSQL 17 with `pgvector` (HNSW index) and a generated `tsvector` column (GIN index) |
| **Retrieval** | vector + keyword, fused with Reciprocal Rank Fusion (no score normalisation needed) |
| **LLM** | pluggable: Claude (default), OpenAI, Ollama, and a deterministic fixture provider for CI |
| **Evals** | golden question set, with recall@k and MRR computed in CI as a **gate**. LLM-judged faithfulness runs when a real model is configured |
| **MCP** | `search_docs` and `ask` tools, so Claude Desktop / Claude Code / any MCP client can use the knowledge base |

Key decisions are recorded as ADRs:

- [ADR-0001](docs/adr/0001-hybrid-retrieval-with-rrf.md): Hybrid retrieval fused with Reciprocal Rank Fusion
- [ADR-0002](docs/adr/0002-local-embeddings-by-default.md): Local embeddings by default, behind an interface
- [ADR-0003](docs/adr/0003-citations-are-verified-not-trusted.md): Citations are verified, not trusted, and the system says "I don't know"
- [ADR-0004](docs/adr/0004-retrieval-evals-gate-ci.md): Retrieval evals gate CI. Answer evals are separate and opt-in

## Ingestion

- **Heading-aware chunking** (LangChain `MarkdownHeaderTextSplitter`, then `RecursiveCharacterTextSplitter` only
  inside sections that are too long). A chunk never straddles two sections, and each carries a breadcrumb
  (`On-call rotation > Paging policy`) that is embedded with it, so chunks that read alike out of context stay distinguishable.
- **Idempotent and incremental:** documents are keyed by `source` and a SHA-256 of their content. Unchanged
  documents are skipped, changed ones are re-chunked in place, and `--prune` mirrors a directory exactly.
  Switching embedding model forces re-embedding, because the model is stored per chunk.
- **One store:** `chunks.embedding vector(384)` with an HNSW index, plus a generated, weighted
  `tsvector` (heading > body) with a GIN index, ready for hybrid retrieval.

```bash
make up && make ingest        # PostgreSQL + API, then index corpus/ (a sample engineering handbook)
make test                     # unit + integration tests against pgvector
```

## Retrieval and evals

`POST /search {"query": "...", "top_k": 5, "mode": "hybrid|vector|keyword"}` returns chunks with their source,
heading breadcrumb, fused score and **each retriever's rank** (so you can see why a chunk ranked where it did).
Vector and keyword candidates (20 each) come from one PostgreSQL round-trip each and are fused with RRF (`k = 60`).

The **retrieval eval** runs in CI with the real model (`bge-small-en-v1.5`) on 35 labelled questions over `corpus/`.
Many questions are paraphrased away from the document wording ("how long can I stay home sick without a doctor's note?").
A hit counts only if it comes from the right document **and** the right section.

| mode | recall@5 | MRR | misses |
|---|---|---|---|
| vector | 0.971 | 0.911 | q04 |
| keyword | 0.943 | 0.830 | q15, q19 |
| **hybrid (RRF)** | **0.971** | 0.887 | q19 |

**Honest reading:** on this small, clean corpus, dense retrieval alone is already strong. Hybrid matches its recall
but has a slightly *lower* MRR, because keyword ranks occasionally pull a relevant chunk down one place. Hybrid stays
the default because it rescues exact-token queries (codes, numbers, acronyms) that dense search misses on larger
corpora (q04 is rescued here). The CI gate fails below recall@5 0.94 / MRR 0.85, set just under the measured baseline.
Tuning RRF weights against this set without a held-out split would overfit, so that waits for a larger golden set.

```bash
python -m evals.retrieval_eval --check     # needs DATABASE_URL; ingests corpus/ and prints the table
```

## Answers with verified citations

`POST /ask {"question": "..."}` → `{answer, abstained, reason, citations: [{n, chunk_id, source, heading}], sources}`

1. Retrieve the top 5 passages (hybrid).
2. **Stage 1 abstain:** if the best cosine similarity is below 0.62 (calibrated on the golden set, see ADR-0003),
   answer "I couldn't find this" **without calling the model**, and list the closest sources.
3. Otherwise the model (Claude by default, OpenAI, Ollama, or fixtures) returns structured output
   `{answerable, answer, citations}`, with inline `[n]` markers.
4. **Verification:** citations must point at retrieved passages, inline markers must match the declared citations,
   and an answerable reply must cite something. A failing reply gets one corrective retry with the exact problems, then
   abstains (`unverifiable_citations`).
5. **Stage 2 abstain:** the model may say the passages don't contain the answer (`not_in_context`).

The prompt treats documents as untrusted input (prompt-injection guard).

## Roadmap

| # | Milestone | Status |
|---|---|---|
| 1 | Ingestion: heading-aware chunking, local embeddings, pgvector schema, `POST /ingest`, CLI | ✅ done (#1) |
| 2 | Hybrid retrieval (vector + full-text + RRF), `POST /search`, retrieval eval gating CI | ✅ done (#2) |
| 3 | Cited answers: providers, two-stage abstain, citation verification, `POST /ask` | ✅ done (#3) |
| 4 | MCP server (`search_docs`, `ask`) | planned |
| 5 | Answer evals (LLM-judged faithfulness and relevance), report | planned |

## Licence

MIT
