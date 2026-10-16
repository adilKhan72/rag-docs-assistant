from typing import Any

import pytest

from ragdocs.answer import SYSTEM_PROMPT, ModelAnswer, answer_question, verify
from ragdocs.llm.base import ProviderRefusal
from ragdocs.retrieval import Hit


class ScriptedProvider:
    name = "scripted"

    def __init__(self, *responses: Any):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def complete_json(self, system, user, schema):
        self.calls.append({"system": system, "user": user, "schema": schema})
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def complete_text(self, system, user):
        raise NotImplementedError


def hit(chunk_id: int, heading: str, content: str, similarity: float = 0.8) -> Hit:
    return Hit(chunk_id=chunk_id, source=f"{heading.split(' > ')[0].lower()}.md", title="t", heading=heading,
               content=content, score=0.03, similarity=similarity)


HITS = [
    hit(11, "Leave policy > Parental leave", "Primary caregivers receive 20 weeks; secondary caregivers 6 weeks."),
    hit(12, "Leave policy > Sick leave", "A doctor's note is required after 3 consecutive working days."),
]


def ask(provider, hits=HITS, threshold=0.62):
    return answer_question("How long is secondary caregiver leave?", hits, provider, threshold)


def test_weak_retrieval_abstains_without_calling_the_model():
    provider = ScriptedProvider()

    result = ask(provider, hits=[hit(1, "Expenses > Limits", "meals", similarity=0.55)])

    assert result.abstained and result.reason == "weak_retrieval"
    assert provider.calls == []
    assert result.sources[0].heading == "Expenses > Limits"


def test_a_cited_answer_maps_citations_back_to_chunks():
    provider = ScriptedProvider({"answerable": True, "answer": "Secondary caregivers get 6 weeks [1].", "citations": [1]})

    result = ask(provider)

    assert not result.abstained
    assert [(c.n, c.chunk_id, c.heading) for c in result.citations] == [(1, 11, "Leave policy > Parental leave")]
    call = provider.calls[0]
    assert call["system"] == SYSTEM_PROMPT
    assert "[1] (Leave policy > Parental leave)" in call["user"] and "[2] (Leave policy > Sick leave)" in call["user"]


def test_the_model_can_say_the_answer_is_not_in_context():
    provider = ScriptedProvider({"answerable": False, "answer": "The passages don't cover bonuses.", "citations": []})

    result = ask(provider)

    assert result.abstained and result.reason == "not_in_context"


def test_invented_citations_get_one_corrective_retry():
    bad = {"answerable": True, "answer": "6 weeks [3].", "citations": [3]}
    good = {"answerable": True, "answer": "6 weeks [1].", "citations": [1]}
    provider = ScriptedProvider(bad, good)

    result = ask(provider)

    assert not result.abstained and result.attempts == 2
    assert "do not refer to provided passages" in provider.calls[1]["user"]


def test_persistently_unverifiable_answers_abstain():
    uncited = {"answerable": True, "answer": "Six weeks.", "citations": []}

    result = ask(ScriptedProvider(uncited, uncited))

    assert result.abstained and result.reason == "unverifiable_citations"


def test_refusal_abstains():
    assert ask(ScriptedProvider(ProviderRefusal("no"))).reason == "model_refusal"


@pytest.mark.parametrize(
    "reply,problem",
    [
        ({"answerable": True, "answer": "x [1]", "citations": [1, 9]}, "do not refer"),
        ({"answerable": True, "answer": "x [2]", "citations": [1]}, "missing from citations"),
        ({"answerable": True, "answer": "x", "citations": [1]}, "no inline"),
        ({"answerable": False, "answer": "x", "citations": [1]}, "must not cite"),
    ],
)
def test_verify_rejects_structural_problems(reply, problem):
    assert any(problem in p for p in verify(ModelAnswer.model_validate(reply), passages=2))


def test_ask_endpoint_end_to_end_with_scripted_provider(db, embedder):
    from pathlib import Path

    from fastapi.testclient import TestClient

    from ragdocs.api import app
    from ragdocs.config import settings
    from ragdocs.embeddings import get_embedder
    from ragdocs.ingest import ingest, load_directory
    from ragdocs.llm.factory import get_provider

    ingest(db, load_directory(Path(__file__).resolve().parents[1] / "corpus"), embedder)
    provider = ScriptedProvider({"answerable": True, "answer": "USD 150 per week [1].", "citations": [1]})
    app.dependency_overrides[get_embedder] = lambda: embedder
    app.dependency_overrides[get_provider] = lambda: provider
    original = settings.abstain_below_similarity
    settings.abstain_below_similarity = 0.0  # the fake embedder's similarities aren't calibrated
    try:
        with TestClient(app) as client:
            body = client.post("/ask", json={"question": "What is the on-call stipend?"}).json()
    finally:
        settings.abstain_below_similarity = original
        app.dependency_overrides.clear()

    assert body["abstained"] is False
    assert body["provider"] == "scripted"
    assert body["citations"][0]["n"] == 1
    assert len(body["sources"]) == settings.context_chunks
