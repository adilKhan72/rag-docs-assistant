import json
from typing import Any

import httpx

from ragdocs.llm.base import ProviderError, ProviderRefusal


class OpenAIProvider:
    """Chat Completions with strict JSON-schema output, over plain HTTP to avoid a second SDK."""

    name = "openai"

    def __init__(self, model: str, api_key: str | None, client: httpx.Client | None = None):
        if not api_key:
            raise ProviderError("OPENAI_API_KEY is not set")
        self.model = model
        self.client = client or httpx.Client(
            base_url="https://api.openai.com/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=120,
        )

    def _chat(self, system: str, user: str, response_format: dict[str, Any] | None = None) -> str:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        if response_format:
            body["response_format"] = response_format

        try:
            response = self.client.post("/chat/completions", json=body)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ProviderError(f"openai error {e.response.status_code}") from e
        except httpx.HTTPError as e:
            raise ProviderError("openai unreachable") from e

        message = response.json()["choices"][0]["message"]
        if message.get("refusal"):
            raise ProviderRefusal(f"model declined: {message['refusal']}")
        return message.get("content") or ""

    def complete_json(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        text = self._chat(
            system,
            user,
            {"type": "json_schema", "json_schema": {"name": "extraction", "schema": schema, "strict": True}},
        )
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ProviderError("openai returned non-JSON despite json_schema output") from e

    def complete_text(self, system: str, user: str) -> str:
        return self._chat(system, user)
