import json
from typing import Any

import anthropic

from ragdocs.llm.base import ProviderError, ProviderRefusal

# `fallbacks: "default"` re-runs a policy-declined request on Anthropic's recommended fallback
# model inside the same call, routed by refusal category. Its beta header is specific to this form.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str, api_key: str | None = None, client: anthropic.Anthropic | None = None):
        self.model = model
        # No api_key → the SDK resolves ANTHROPIC_API_KEY / an `ant auth login` profile itself.
        self.client = client or anthropic.Anthropic(api_key=api_key)

    def _create(self, system: str, user: str, output_format: dict[str, Any] | None = None):
        output_config: dict[str, Any] = {"effort": "medium"}
        if output_format is not None:
            output_config["format"] = output_format

        try:
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                betas=[FALLBACK_BETA],
                fallbacks="default",
                output_config=output_config,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.RateLimitError as e:
            raise ProviderError(f"anthropic rate limited: {e.message}") from e
        except anthropic.APIStatusError as e:
            raise ProviderError(f"anthropic error {e.status_code}: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise ProviderError("anthropic unreachable") from e

        # Check before reading content: a refusal can arrive with empty or partial content.
        if response.stop_reason == "refusal":
            category = response.stop_details.category if response.stop_details else None
            raise ProviderRefusal(f"model declined (category={category})")
        if response.stop_reason == "max_tokens":
            raise ProviderError("anthropic response truncated at max_tokens")

        return next((block.text for block in response.content if block.type == "text"), "")

    def complete_json(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        text = self._create(system, user, {"type": "json_schema", "schema": schema})
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ProviderError("anthropic returned non-JSON despite json_schema output") from e

    def complete_text(self, system: str, user: str) -> str:
        return self._create(system, user)
