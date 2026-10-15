-- Applied idempotently by ragdocs.db.migrate().
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id            BIGSERIAL PRIMARY KEY,
    source        TEXT NOT NULL UNIQUE,          -- stable identifier, e.g. a relative file path
    title         TEXT NOT NULL,
    content_hash  CHAR(64) NOT NULL,             -- skip re-embedding unchanged documents
    ingested_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id              BIGSERIAL PRIMARY KEY,
    document_id     BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index     INT NOT NULL,
    heading         TEXT NOT NULL,               -- "Doc title > Section > Subsection"
    content         TEXT NOT NULL,
    embedding       vector(384) NOT NULL,
    embedding_model TEXT NOT NULL,               -- queries never mix models (ADR-0002)
    tsv             tsvector GENERATED ALWAYS AS (
                        setweight(to_tsvector('english', heading), 'A') ||
                        setweight(to_tsvector('english', content), 'B')
                    ) STORED,
    UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_tsv_gin ON chunks USING gin (tsv);
