from typing import Any, Protocol


class ProviderError(Exception):
    """The provider could not produce a response (network, auth, rate limit, bad output). Retry-worthy upstream."""


class ProviderRefusal(ProviderError):
    """The model declined the request on policy grounds. Not retried: route the document to human review."""


class LLMProvider(Protocol):
    """The only surface the rest of the service sees (docs/adr/0003-pluggable-llm-providers.md).

    Adapters use each vendor's native structured-output feature inside complete_json, so callers
    always get a parsed dict back and never deal with vendor-specific response shapes.
    """

    name: str

    def complete_json(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]: ...

    def complete_text(self, system: str, user: str) -> str: ...
