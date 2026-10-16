from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from ragdocs.db import connect, migrate
from ragdocs.embeddings import Embedder, get_embedder
from ragdocs.ingest import SourceDocument, ingest
from ragdocs.retrieval import Mode, search


@asynccontextmanager
async def lifespan(_: FastAPI):
    with connect() as conn:
        migrate(conn)
    yield


app = FastAPI(title="rag-docs-assistant", version="0.1.0", lifespan=lifespan)


class DocumentIn(BaseModel):
    source: str = Field(min_length=1, max_length=500)
    text: str = Field(min_length=1, max_length=500_000)
    title: str | None = None


class IngestRequest(BaseModel):
    documents: list[DocumentIn] = Field(min_length=1, max_length=500)
    prune: bool = False


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ingest")
def ingest_documents(request: IngestRequest, embedder: Embedder = Depends(get_embedder)) -> dict:
    docs = [SourceDocument(d.source, d.text, d.title) for d in request.documents]
    with connect() as conn:
        return asdict(ingest(conn, docs, embedder, prune=request.prune))


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    mode: Mode = "hybrid"


@app.post("/search")
def search_chunks(request: SearchRequest, embedder: Embedder = Depends(get_embedder)) -> dict:
    with connect() as conn:
        hits = search(conn, embedder, request.query, request.top_k, request.mode)
    return {"query": request.query, "mode": request.mode, "hits": [asdict(h) for h in hits]}
