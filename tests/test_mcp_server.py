import asyncio
from pathlib import Path

import pytest

from ragdocs import mcp_server
from ragdocs.ingest import ingest, load_directory
from tests.test_answer import ScriptedProvider

CORPUS = Path(__file__).resolve().parents[1] / "corpus"


def run(coro):
    return asyncio.run(coro)


def test_tools_are_advertised_with_typed_schemas():
    tools = {t.name: t for t in run(mcp_server.server.list_tools())}

    assert set(tools) == {"search_docs", "ask"}
    assert tools["search_docs"].input_schema["required"] == ["query"]
    assert tools["search_docs"].input_schema["properties"]["top_k"]["default"] == 5
    assert tools["ask"].input_schema["required"] == ["question"]
    # Typed outputs: clients get schemas, not free text.
    assert "abstained" in tools["ask"].output_schema["properties"]
    assert tools["search_docs"].output_schema is not None


@pytest.fixture
def indexed(db, embedder, monkeypatch):
    ingest(db, load_directory(CORPUS), embedder)
    monkeypatch.setattr(mcp_server, "get_embedder", lambda: embedder)
    return db


def test_search_docs_tool_returns_passages(indexed):
    result = run(mcp_server.server.call_tool("search_docs", {"query": "canary traffic percentage", "top_k": 3}))

    assert not result.is_error
    passages = result.structured_content["result"]
    assert len(passages) == 3
    assert passages[0]["source"] == "deployments.md"
    assert {"source", "heading", "content", "similarity", "chunk_id"} <= set(passages[0])


def test_search_docs_clamps_top_k(indexed):
    result = run(mcp_server.server.call_tool("search_docs", {"query": "leave", "top_k": 500}))

    assert len(result.structured_content["result"]) <= 20


def test_ask_tool_returns_a_cited_answer(indexed, monkeypatch):
    provider = ScriptedProvider({"answerable": True, "answer": "USD 150 per week [1].", "citations": [1]})
    monkeypatch.setattr(mcp_server, "get_provider", lambda: provider)
    monkeypatch.setattr(mcp_server.settings, "abstain_below_similarity", 0.0)

    result = run(mcp_server.server.call_tool("ask", {"question": "What is the on-call stipend?"}))

    assert not result.is_error
    body = result.structured_content
    assert body["abstained"] is False
    assert body["citations"][0]["n"] == 1
