import json
from typing import Any

import httpx

from ragdocs.llm.base import ProviderError


class OllamaProvider:
    """Local model via Ollama. `format` takes a JSON schema and constrains decoding to it."""

    name = "ollama"

    def __init__(self, model: str, base_url: str, client: httpx.Client | None = None):
        self.model = model
        self.client = client or httpx.Client(base_url=base_url, timeout=300)

    def _chat(self, system: str, user: str, schema: dict[str, Any] | None = None) -> str:
        body: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            # Extraction should be repeatable, not creative.
            "options": {"temperature": 0},
        }
        if schema is not None:
            body["format"] = schema

        try:
            response = self.client.post("/api/chat", json=body)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ProviderError(f"ollama error {e.response.status_code}: is model {self.model!r} pulled?") from e
        except httpx.HTTPError as e:
            raise ProviderError("ollama unreachable") from e

        return response.json()["message"]["content"]

    def complete_json(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        text = self._chat(system, user, schema)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ProviderError("ollama returned non-JSON") from e

    def complete_text(self, system: str, user: str) -> str:
        return self._chat(system, user)
