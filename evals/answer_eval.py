"""Answer eval (ADR-0004): runs every golden question through /ask's pipeline and grades the result.

Needs a real model, so it is opt-in and not a CI gate (it costs money and varies run to run):
    LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=... python -m evals.answer_eval
Writes evals/reports/<date>-<provider>.md.

Per answerable question:
- retrieval_hit: the expected section is among the passages the answer CITED (cheap, deterministic)
- faithful: an LLM judge confirms every claim is supported by the cited passages
- correct: the judge confirms the answer actually answers the question
Per unanswerable question:
- abstained: the system declined (any abstain reason)
"""

import datetime
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from ragdocs.answer import Answer, answer_question
from ragdocs.config import settings
from ragdocs.llm.base import LLMProvider

ROOT = Path(__file__).resolve().parents[1]

JUDGE_PROMPT = """You grade answers produced by a documentation assistant. You are given a question, the passages the
answer cited, and the answer. Judge strictly and only from the passages.
- faithful: every factual claim in the answer is supported by the cited passages (no outside facts, no distortion).
- correct: the answer directly and completely answers the question.
Give a one-sentence rationale."""


class Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    faithful: bool
    correct: bool
    rationale: str


@dataclass
class Graded:
    id: str
    answerable: bool
    abstained: bool
    reason: str | None
    retrieval_hit: bool | None = None
    faithful: bool | None = None
    correct: bool | None = None
    rationale: str = ""


def _judge_schema() -> dict:
    schema = Verdict.model_json_schema()
    schema.pop("title", None)
    for prop in schema["properties"].values():
        prop.pop("title", None)
    return schema


def grade(question: dict, answer: Answer, hits_by_n: dict, judge: LLMProvider) -> Graded:
    expected = question["expected"]
    graded = Graded(question["id"], expected is not None, answer.abstained, answer.reason)
    if expected is None or answer.abstained:
        return graded

    cited = [hits_by_n[c.n] for c in answer.citations]
    graded.retrieval_hit = any(
        h.source == expected["source"] and expected["section"].lower() in h.heading.lower() for h in cited
    )
    passages = "\n\n".join(f"[{c.n}] ({hits_by_n[c.n].heading})\n{hits_by_n[c.n].content}" for c in answer.citations)
    verdict = Verdict.model_validate(
        judge.complete_json(
            JUDGE_PROMPT,
            f"Question: {question['question']}\n\nCited passages:\n{passages}\n\nAnswer:\n{answer.answer}",
            _judge_schema(),
        )
    )
    graded.faithful, graded.correct, graded.rationale = verdict.faithful, verdict.correct, verdict.rationale
    return graded


def summarise(results: list[Graded]) -> dict:
    answerable = [r for r in results if r.answerable]
    unanswerable = [r for r in results if not r.answerable]
    answered = [r for r in answerable if not r.abstained]

    def rate(xs: list[bool]) -> float:
        return round(sum(xs) / len(xs), 3) if xs else 0.0

    return {
        "answered_rate": rate([not r.abstained for r in answerable]),  # coverage on answerable questions
        "faithfulness": rate([bool(r.faithful) for r in answered]),
        "correctness": rate([bool(r.correct) for r in answered]),
        "cited_right_section": rate([bool(r.retrieval_hit) for r in answered]),
        "abstention_accuracy": rate([r.abstained for r in unanswerable]),
        "n_answerable": len(answerable),
        "n_unanswerable": len(unanswerable),
    }


def render(summary: dict, results: list[Graded], provider: str, date: str) -> str:
    lines = [f"# Answer eval — {date} — provider `{provider}`", "", "| metric | value |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in summary.items()]
    lines += ["", "| id | abstained | reason | cited right section | faithful | correct | rationale |", "|---|---|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r.id} | {r.abstained} | {r.reason or ''} | {r.retrieval_hit} | {r.faithful} | {r.correct} | {r.rationale} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    from ragdocs.db import connect, migrate
    from ragdocs.embeddings import get_embedder
    from ragdocs.ingest import ingest, load_directory
    from ragdocs.llm.factory import get_provider
    from ragdocs.retrieval import search

    provider = get_provider()
    if provider.name == "fixture":
        raise SystemExit("answer eval needs a real model: set LLM_PROVIDER (anthropic|openai|ollama) and its key")

    golden = [json.loads(line) for line in (ROOT / "evals" / "golden.jsonl").read_text().splitlines()]
    embedder = get_embedder()
    results = []
    with connect() as conn:
        migrate(conn)
        ingest(conn, load_directory(ROOT / "corpus"), embedder, prune=True)
        for q in golden:
            hits = search(conn, embedder, q["question"], top_k=settings.context_chunks)
            answer = answer_question(q["question"], hits, provider, settings.abstain_below_similarity)
            results.append(grade(q, answer, {n: h for n, h in enumerate(hits, start=1)}, provider))

    summary = summarise(results)
    date = datetime.date.today().isoformat()
    out = ROOT / "evals" / "reports" / f"{date}-{provider.name}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(render(summary, results, provider.name, date))
    print(json.dumps(summary, indent=2))
    print(f"report: {out}")


if __name__ == "__main__":
    main()
