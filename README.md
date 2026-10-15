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

## Roadmap

| # | Milestone | Status |
|---|---|---|
| 1 | Ingestion: heading-aware chunking, local embeddings, pgvector schema, `POST /ingest`, CLI | in progress |
| 2 | Hybrid retrieval (vector + full-text + RRF), `POST /search`, retrieval eval gating CI | planned |
| 3 | Cited answers: providers, refusal on weak evidence, citation verification, `POST /ask` | planned |
| 4 | MCP server (`search_docs`, `ask`) | planned |
| 5 | Answer evals (LLM-judged faithfulness and relevance), report | planned |

## Licence

MIT
