from evals.answer_eval import Graded, grade, render, summarise
from ragdocs.answer import Answer, Citation
from ragdocs.retrieval import Hit
from tests.test_answer import ScriptedProvider

HIT = Hit(chunk_id=1, source="leave-policy.md", title="t", heading="Leave policy > Parental leave",
          content="Secondary caregivers receive 6 weeks.", score=0.03, similarity=0.8)
Q = {"id": "q24", "question": "How many weeks for a secondary caregiver?", "expected": {"source": "leave-policy.md", "section": "Parental leave"}}


def answered(text="6 weeks [1]."):
    return Answer(text, False, None, citations=[Citation(1, 1, "leave-policy.md", HIT.heading)])


def test_grade_records_cited_section_and_judge_verdict():
    judge = ScriptedProvider({"faithful": True, "correct": True, "rationale": "Supported by [1]."})

    g = grade(Q, answered(), {1: HIT}, judge)

    assert (g.retrieval_hit, g.faithful, g.correct) == (True, True, True)
    assert "Cited passages:\n[1] (Leave policy > Parental leave)" in judge.calls[0]["user"]


def test_abstentions_and_unanswerables_are_not_judged():
    judge = ScriptedProvider()

    abstained = grade(Q, Answer("no", True, "weak_retrieval"), {}, judge)
    unanswerable = grade({"id": "u1", "question": "401k?", "expected": None}, Answer("no", True, "not_in_context"), {}, judge)

    assert abstained.faithful is None and unanswerable.abstained
    assert judge.calls == []


def test_summary_separates_coverage_quality_and_abstention():
    results = [
        Graded("q1", True, False, None, True, True, True),
        Graded("q2", True, False, None, False, False, True),
        Graded("q3", True, True, "weak_retrieval"),
        Graded("u1", False, True, "not_in_context"),
        Graded("u2", False, False, None),
    ]

    s = summarise(results)

    assert s["answered_rate"] == 0.667
    assert s["faithfulness"] == 0.5 and s["correctness"] == 1.0 and s["cited_right_section"] == 0.5
    assert s["abstention_accuracy"] == 0.5
    assert "| q3 | True | weak_retrieval |" in render(s, results, "anthropic", "2026-10-16")
