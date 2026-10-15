import hashlib
import math
import os
from typing import Sequence

import psycopg
import pytest

from ragdocs.db import connect, migrate


class FakeEmbedder:
    """Deterministic bag-of-words embedder: texts sharing words get similar vectors. Enough to test plumbing
    without downloading a model; retrieval quality is measured with the real model in the eval."""

    model = "fake-bow-384"
    dim = 384

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for word in text.lower().split():
            vector[int(hashlib.md5(word.strip(".,:;()`*").encode()).hexdigest(), 16) % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


@pytest.fixture
def embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def db():
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set (integration tests need PostgreSQL with pgvector)")
    try:
        with connect(url) as conn:
            migrate(conn)
            conn.execute("TRUNCATE documents RESTART IDENTITY CASCADE")
            conn.commit()
            yield conn
    except psycopg.OperationalError as e:
        pytest.skip(f"database unavailable: {e}")
