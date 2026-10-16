import hashlib
import json
from pathlib import Path
from typing import Any

from ragdocs.llm.base import LLMProvider, ProviderError

DEFAULT_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "llm"


class FixtureMissingError(ProviderError):
    pass


def fixture_key(kind: str, system: str, user: str, schema: dict[str, Any] | None = None) -> str:
    """Stable hash of everything that determines a model's answer.

    Any prompt or schema change produces a new key, so the change shows up in review as new
    fixture files instead of silently reusing a stale answer.
    """
    payload = json.dumps({"kind": kind, "system": system, "user": user, "schema": schema}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


class FixtureProvider:
    """Deterministic provider for tests, CI and demos: answers from files on disk, never the network.

    With `record_with` set, a cache miss is answered by that real provider and the answer is saved,
    which is how fixtures get created once an API key is available.
    """

    name = "fixture"

    def __init__(self, fixture_dir: Path = DEFAULT_FIXTURE_DIR, record_with: LLMProvider | None = None):
        self.fixture_dir = fixture_dir
        self.record_with = record_with

    def _path(self, key: str) -> Path:
        return self.fixture_dir / f"{key}.json"

    def _load(self, key: str) -> Any:
        path = self._path(key)
        if path.exists():
            return json.loads(path.read_text())["response"]
        return None

    def save(self, kind: str, system: str, user: str, schema: dict[str, Any] | None, response: Any) -> Path:
        key = fixture_key(kind, system, user, schema)
        self.fixture_dir.mkdir(parents=True, exist_ok=True)
        path = self._path(key)
        path.write_text(json.dumps({"kind": kind, "response": response}, indent=2, sort_keys=True) + "\n")
        return path

    def _missing(self, key: str) -> FixtureMissingError:
        return FixtureMissingError(
            f"no fixture {key}.json in {self.fixture_dir}; record one with a real provider "
            "(FixtureProvider(record_with=...)) or switch LLM_PROVIDER"
        )

    def complete_json(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        key = fixture_key("json", system, user, schema)
        cached = self._load(key)
        if cached is not None:
            return cached
        if self.record_with is None:
            raise self._missing(key)
        response = self.record_with.complete_json(system, user, schema)
        self.save("json", system, user, schema, response)
        return response

    def complete_text(self, system: str, user: str) -> str:
        key = fixture_key("text", system, user)
        cached = self._load(key)
        if cached is not None:
            return cached
        if self.record_with is None:
            raise self._missing(key)
        response = self.record_with.complete_text(system, user)
        self.save("text", system, user, None, response)
        return response
