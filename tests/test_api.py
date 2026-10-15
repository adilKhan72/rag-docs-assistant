import os

import pytest
from fastapi.testclient import TestClient

from ragdocs.api import app
from ragdocs.embeddings import get_embedder


@pytest.fixture
def client(db, embedder):
    app.dependency_overrides[get_embedder] = lambda: embedder
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_ingest_endpoint_reports_what_changed(client):
    payload = {"documents": [{"source": "x.md", "text": "# X\n\n## Part\nhello world"}]}

    first = client.post("/ingest", json=payload).json()
    second = client.post("/ingest", json=payload).json()

    assert first["added"] == ["x.md"] and first["chunks_written"] == 1
    assert second["unchanged"] == ["x.md"]


def test_ingest_validates_input(client):
    assert client.post("/ingest", json={"documents": []}).status_code == 422
