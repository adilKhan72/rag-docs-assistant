from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://rag:rag@localhost:5432/rag"

    # Local ONNX model (ADR-0002). The schema's vector column is sized to match.
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    chunk_size: int = 800
    chunk_overlap: int = 100

    # ADR-0003: below this best-hit cosine similarity the question is treated as off-topic and the model isn't
    # called. Calibrated with evals/calibrate_abstain.py (no answerable golden question falls below it).
    abstain_below_similarity: float = 0.62
    context_chunks: int = 5

    # fixture | anthropic | openai | ollama. fixture needs no keys or network (tests, CI, demos).
    llm_provider: str = "fixture"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-5-5"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"


settings = Settings()
