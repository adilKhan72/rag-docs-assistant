"""MCP server exposing the knowledge base to MCP clients (Claude Desktop, Claude Code, IDEs).

Run over stdio:  python -m ragdocs.mcp_server
Claude Code:     claude mcp add ragdocs -- python -m ragdocs.mcp_server   (with DATABASE_URL in the environment)
"""

from dataclasses import asdict

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel

from ragdocs.answer import answer_question
from ragdocs.config import settings
from ragdocs.db import connect
from ragdocs.embeddings import get_embedder
from ragdocs.llm.factory import get_provider
from ragdocs.retrieval import search

server = MCPServer(
    name="ragdocs",
    instructions=(
        "Search and answer questions about the indexed internal documentation. Prefer `ask` for direct questions; "
        "it returns an answer with verified citations or says the docs don't cover it. Use `search_docs` to browse "
        "passages yourself. Always cite the returned sources."
    ),
)


class Passage(BaseModel):
    source: str
    heading: str
    content: str
    similarity: float | None
    chunk_id: int


class CitationOut(BaseModel):
    n: int
    chunk_id: int
    source: str
    heading: str


class AskResult(BaseModel):
    """Typed so MCP clients get an output schema, not free text."""

    answer: str
    abstained: bool
    reason: str | None
    citations: list[CitationOut]
    sources: list[CitationOut]


@server.tool(description="Hybrid (semantic + keyword) search over the documentation. Returns passages with source, section heading and relevance.")
def search_docs(query: str, top_k: int = 5) -> list[Passage]:
    top_k = max(1, min(top_k, 20))
    with connect() as conn:
        hits = search(conn, get_embedder(), query, top_k=top_k)
    return [Passage(source=h.source, heading=h.heading, content=h.content, similarity=h.similarity, chunk_id=h.chunk_id) for h in hits]


@server.tool(description="Answer a question from the documentation with verified [n] citations, or abstain with the reason if the docs don't contain it.")
def ask(question: str) -> AskResult:
    with connect() as conn:
        hits = search(conn, get_embedder(), question, top_k=settings.context_chunks)
    result = asdict(answer_question(question, hits, get_provider(), settings.abstain_below_similarity))
    result.pop("attempts")
    return AskResult.model_validate(result)


if __name__ == "__main__":
    server.run("stdio")
