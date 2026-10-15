import hashlib
from dataclasses import dataclass
from pathlib import Path

import psycopg

from ragdocs.chunking import chunk_markdown, title_of
from ragdocs.embeddings import Embedder


@dataclass(frozen=True)
class SourceDocument:
    source: str
    text: str
    title: str | None = None


@dataclass
class IngestReport:
    added: list[str]
    updated: list[str]
    unchanged: list[str]
    removed: list[str]
    chunks_written: int


def ingest(conn: psycopg.Connection, documents: list[SourceDocument], embedder: Embedder, prune: bool = False) -> IngestReport:
    """Idempotent: unchanged documents (same content hash and embedding model) are skipped, changed ones are
    re-chunked and re-embedded in place. With prune=True, documents not in this batch are removed, which keeps the
    index an exact mirror of a directory."""
    report = IngestReport([], [], [], [], 0)

    for doc in documents:
        digest = hashlib.sha256(doc.text.encode()).hexdigest()
        row = conn.execute(
            "SELECT d.id, d.content_hash, (SELECT min(embedding_model) FROM chunks WHERE document_id = d.id) "
            "FROM documents d WHERE d.source = %s",
            (doc.source,),
        ).fetchone()

        if row and row[1] == digest and row[2] == embedder.model:
            report.unchanged.append(doc.source)
            continue

        title = doc.title or title_of(doc.text, fallback=Path(doc.source).stem.replace("-", " ").title())
        chunks = chunk_markdown(doc.text, title)
        vectors = embedder.embed_documents([c.embedding_text for c in chunks]) if chunks else []

        if row:
            document_id = row[0]
            conn.execute("DELETE FROM chunks WHERE document_id = %s", (document_id,))
            conn.execute(
                "UPDATE documents SET title = %s, content_hash = %s, ingested_at = now() WHERE id = %s",
                (title, digest, document_id),
            )
            report.updated.append(doc.source)
        else:
            document_id = conn.execute(
                "INSERT INTO documents (source, title, content_hash) VALUES (%s, %s, %s) RETURNING id",
                (doc.source, title, digest),
            ).fetchone()[0]
            report.added.append(doc.source)

        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO chunks (document_id, chunk_index, heading, content, embedding, embedding_model) "
                "VALUES (%s, %s, %s, %s, %s::vector, %s)",
                [(document_id, c.index, c.heading, c.content, vector, embedder.model) for c, vector in zip(chunks, vectors)],
            )
        report.chunks_written += len(chunks)

    if prune:
        keep = [d.source for d in documents]
        removed = conn.execute("DELETE FROM documents WHERE NOT (source = ANY(%s)) RETURNING source", (keep,)).fetchall()
        report.removed = [r[0] for r in removed]

    conn.commit()
    return report


def load_directory(root: Path) -> list[SourceDocument]:
    return [
        SourceDocument(source=str(path.relative_to(root)), text=path.read_text(encoding="utf-8"))
        for path in sorted(root.rglob("*"))
        if path.suffix in {".md", ".txt"} and path.is_file()
    ]
