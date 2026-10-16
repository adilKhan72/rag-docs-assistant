"""Calibrate the abstain threshold (ADR-0003) from data: best-hit cosine similarity for answerable vs unanswerable
golden questions, with the real embedding model. Prints both distributions and the cleanest separating threshold.

Usage:  python -m evals.calibrate_abstain   (needs DATABASE_URL)
"""

import json
from pathlib import Path

from ragdocs.db import connect, migrate
from ragdocs.embeddings import get_embedder
from ragdocs.ingest import ingest, load_directory
from ragdocs.retrieval import search

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    golden = [json.loads(line) for line in (ROOT / "evals" / "golden.jsonl").read_text().splitlines()]
    embedder = get_embedder()
    with connect() as conn:
        migrate(conn)
        ingest(conn, load_directory(ROOT / "corpus"), embedder, prune=True)
        best = {q["id"]: max((h.similarity for h in search(conn, embedder, q["question"], top_k=5)), default=0.0) for q in golden}

    answerable = sorted(best[q["id"]] for q in golden if q["expected"])
    unanswerable = sorted(best[q["id"]] for q in golden if not q["expected"])
    print("answerable   min/median/max:", answerable[0], answerable[len(answerable) // 2], answerable[-1])
    print("unanswerable min/median/max:", unanswerable[0], unanswerable[len(unanswerable) // 2], unanswerable[-1])
    print("unanswerable:", unanswerable)
    print("lowest answerable:", answerable[:5])

    # Threshold that maximises correct decisions (answer when >= t, abstain when < t).
    candidates = sorted(set(answerable + unanswerable))
    scored = [(sum(a >= t for a in answerable) + sum(u < t for u in unanswerable), t) for t in candidates]
    correct, threshold = max(scored)
    print(f"best threshold {threshold}: {correct}/{len(golden)} correct decisions")


if __name__ == "__main__":
    main()
