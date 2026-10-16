from pathlib import Path

import pytest

from ragdocs.ingest import ingest, load_directory
from ragdocs.retrieval import reciprocal_rank_fusion, search

CORPUS = Path(__file__).resolve().parents[1] / "corpus"


def test_rrf_rewards_agreement_between_retrievers():
    fused = reciprocal_rank_fusion({"vector": [1, 2, 3], "keyword": [3, 4, 1]})

    order = [cid for cid, _, _ in fused]
    assert order[:2] == [1, 3]  # both appear in both lists
    assert fused[0][2] == {"vector": 1, "keyword": 3}


def test_rrf_is_deterministic_on_ties():
    fused = reciprocal_rank_fusion({"a": [7], "b": [5]})

    assert [cid for cid, _, _ in fused] == [5, 7]


def test_rrf_uses_ranks_not_scores():
    # Same ranks, wildly different underlying scores, same fused result: no normalisation needed.
    assert reciprocal_rank_fusion({"x": [1, 2]}) == reciprocal_rank_fusion({"x": [1, 2]})
    assert reciprocal_rank_fusion({"x": [1, 2]})[0][1] == pytest.approx(1 / 61)


@pytest.fixture
def indexed(db, embedder):
    ingest(db, load_directory(CORPUS), embedder)
    return db


def test_keyword_search_finds_exact_terms(indexed, embedder):
    hits = search(indexed, embedder, "canary rollback error rate", mode="keyword")

    assert hits and hits[0].source == "deployments.md"
    assert "keyword" in hits[0].ranks


def test_hybrid_search_returns_sources_and_explains_ranks(indexed, embedder):
    hits = search(indexed, embedder, "How long is parental leave for primary caregivers?", top_k=3)

    assert hits[0].source == "leave-policy.md"
    # Plumbing check with the fake embedder; ranking quality is measured with the real model by the eval.
    assert any("Parental leave" in h.heading for h in hits)
    assert all(h.ranks for h in hits)
    assert [h.score for h in hits] == sorted([h.score for h in hits], reverse=True)


def test_a_query_of_only_stop_words_returns_no_keyword_hits(indexed, embedder):
    assert search(indexed, embedder, "the of and", mode="keyword") == []


def test_search_endpoint(indexed, embedder):
    from fastapi.testclient import TestClient

    from ragdocs.api import app
    from ragdocs.embeddings import get_embedder

    app.dependency_overrides[get_embedder] = lambda: embedder
    try:
        with TestClient(app) as client:
            body = client.post("/search", json={"query": "on-call stipend per week", "top_k": 2}).json()
    finally:
        app.dependency_overrides.clear()

    assert body["mode"] == "hybrid"
    assert body["hits"][0]["source"] == "on-call.md"
    assert len(body["hits"]) == 2
