from functools import lru_cache
from typing import Protocol, Sequence

from ragdocs.config import settings


class Embedder(Protocol):
    model: str
    dim: int

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class FastEmbedder:
    """Local ONNX embeddings (ADR-0002). BGE models expect a query instruction prefix, which
    fastembed's query_embed applies, so queries and passages go through different methods."""

    def __init__(self, model: str = settings.embedding_model, dim: int = settings.embedding_dim):
        from fastembed import TextEmbedding

        self.model = model
        self.dim = dim
        self._model = TextEmbedding(model_name=model)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.passage_embed(list(texts))]

    def embed_query(self, text: str) -> list[float]:
        return next(iter(self._model.query_embed([text]))).tolist()


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    return FastEmbedder()
