from dataclasses import dataclass, field
from typing import Literal

import psycopg

from ragdocs.embeddings import Embedder

Mode = Literal["hybrid", "vector", "keyword"]

RRF_K = 60  # ADR-0001: the standard constant; dampens the advantage of the very top ranks.
CANDIDATES = 20  # depth taken from each retriever before fusion


@dataclass
class Hit:
    chunk_id: int
    source: str
    title: str
    heading: str
    content: str
    score: float
    ranks: dict[str, int] = field(default_factory=dict)  # retriever → 1-based rank, for explainability
    # Cosine similarity to the query (None in keyword-only mode). Unlike the RRF score, it's an absolute
    # relevance signal, so it's what the abstain decision uses (ADR-0003).
    similarity: float | None = None


def _vector_ranked(conn: psycopg.Connection, embedder: Embedder, vector: list[float], limit: int) -> list[int]:
    rows = conn.execute(
        # Only chunks embedded with the same model are comparable (ADR-0002).
        "SELECT id FROM chunks WHERE embedding_model = %s ORDER BY embedding <=> %s::vector LIMIT %s",
        (embedder.model, vector, limit),
    ).fetchall()
    return [r[0] for r in rows]


def _keyword_ranked(conn: psycopg.Connection, query: str, limit: int) -> list[int]:
    # websearch_to_tsquery ANDs terms; for natural-language questions that's too strict, so terms are OR-ed and
    # ranked by ts_rank_cd (rewards terms appearing close together). Stop words drop out of the tsquery.
    rows = conn.execute(
        """
        WITH q AS (
            SELECT to_tsquery('english', string_agg(lexeme, ' | ')) AS query
            FROM unnest(to_tsvector('english', %s))
        )
        SELECT c.id FROM chunks c, q
        WHERE q.query IS NOT NULL AND c.tsv @@ q.query
        ORDER BY ts_rank_cd(c.tsv, q.query) DESC, c.id
        LIMIT %s
        """,
        (query, limit),
    ).fetchall()
    return [r[0] for r in rows]


def reciprocal_rank_fusion(rankings: dict[str, list[int]], k: int = RRF_K) -> list[tuple[int, float, dict[str, int]]]:
    """Fuse ranked id lists by rank only: score(d) = Σ 1 / (k + rank). Ties break by id for determinism."""
    scores: dict[int, float] = {}
    ranks: dict[int, dict[str, int]] = {}
    for name, ids in rankings.items():
        for rank, chunk_id in enumerate(ids, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
            ranks.setdefault(chunk_id, {})[name] = rank
    ordered = sorted(scores, key=lambda cid: (-scores[cid], cid))
    return [(cid, scores[cid], ranks[cid]) for cid in ordered]


def search(conn: psycopg.Connection, embedder: Embedder, query: str, top_k: int = 5, mode: Mode = "hybrid") -> list[Hit]:
    rankings: dict[str, list[int]] = {}
    vector = embedder.embed_query(query) if mode in ("hybrid", "vector") else None
    if vector is not None:
        rankings["vector"] = _vector_ranked(conn, embedder, vector, CANDIDATES)
    if mode in ("hybrid", "keyword"):
        rankings["keyword"] = _keyword_ranked(conn, query, CANDIDATES)

    fused = reciprocal_rank_fusion(rankings)[:top_k]
    if not fused:
        return []

    rows = conn.execute(
        "SELECT c.id, d.source, d.title, c.heading, c.content, "
        "CASE WHEN %s::vector IS NULL THEN NULL ELSE 1 - (c.embedding <=> %s::vector) END "
        "FROM chunks c JOIN documents d ON d.id = c.document_id WHERE c.id = ANY(%s)",
        (vector, vector, [cid for cid, _, _ in fused]),
    ).fetchall()
    by_id = {r[0]: r for r in rows}
    return [
        Hit(
            chunk_id=cid, source=by_id[cid][1], title=by_id[cid][2], heading=by_id[cid][3], content=by_id[cid][4],
            score=round(score, 6), ranks=ranks,
            similarity=None if by_id[cid][5] is None else round(float(by_id[cid][5]), 4),
        )
        for cid, score, ranks in fused
    ]
