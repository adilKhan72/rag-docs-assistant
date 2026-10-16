from functools import lru_cache

from ragdocs.config import Settings, settings
from ragdocs.llm.base import LLMProvider


def build_provider(config: Settings) -> LLMProvider:
    # Local imports: the fixture path (tests, CI) never needs vendor SDKs configured.
    if config.llm_provider == "fixture":
        from ragdocs.llm.fixture import FixtureProvider

        return FixtureProvider()
    if config.llm_provider == "anthropic":
        from ragdocs.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(model=config.anthropic_model, api_key=config.anthropic_api_key)
    if config.llm_provider == "openai":
        from ragdocs.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(model=config.openai_model, api_key=config.openai_api_key)
    if config.llm_provider == "ollama":
        from ragdocs.llm.ollama_provider import OllamaProvider

        return OllamaProvider(model=config.ollama_model, base_url=config.ollama_url)
    raise ValueError(f"unknown LLM_PROVIDER {config.llm_provider!r}")


@lru_cache(maxsize=1)
def get_provider() -> LLMProvider:
    return build_provider(settings)
