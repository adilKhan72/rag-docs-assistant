"""Retrieval eval (ADR-0004): recall@k and MRR per mode on the golden set, with the real embedding model.

A hit counts as relevant when it comes from the expected document AND its heading contains the expected section,
so "right document, wrong section" is a miss. Unanswerable questions are excluded here (they're for answer evals).

Usage:  python -m evals.retrieval_eval [--k 5] [--check]   (needs DATABASE_URL; ingests corpus/ first)
"""

import argparse
import json
import sys
from pathlib import Path

from ragdocs.db import connect, migrate
from ragdocs.embeddings import get_embedder
from ragdocs.ingest import ingest, load_directory
from ragdocs.retrieval import search

ROOT = Path(__file__).resolve().parents[1]
MODES = ("vector", "keyword", "hybrid")


def load_golden() -> list[dict]:
    lines = (ROOT / "evals" / "golden.jsonl").read_text().splitlines()
    return [q for q in map(json.loads, lines) if q["expected"]]


def is_relevant(hit, expected: dict) -> bool:
    return hit.source == expected["source"] and expected["section"].lower() in hit.heading.lower()


def evaluate(conn, embedder, questions: list[dict], k: int) -> dict:
    results = {}
    for mode in MODES:
        recall_hits, reciprocal_ranks, misses = 0, [], []
        for q in questions:
            hits = search(conn, embedder, q["question"], top_k=k, mode=mode)
            rank = next((i for i, h in enumerate(hits, start=1) if is_relevant(h, q["expected"])), None)
            recall_hits += rank is not None
            reciprocal_ranks.append(1 / rank if rank else 0.0)
            if rank is None:
                misses.append(q["id"])
        results[mode] = {
            f"recall@{k}": round(recall_hits / len(questions), 3),
            "mrr": round(sum(reciprocal_ranks) / len(questions), 3),
            "misses": misses,
        }
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--check", action="store_true", help="fail if hybrid falls below evals/thresholds.json")
    args = parser.parse_args()

    embedder = get_embedder()
    questions = load_golden()
    with connect() as conn:
        migrate(conn)
        ingest(conn, load_directory(ROOT / "corpus"), embedder, prune=True)
        results = evaluate(conn, embedder, questions, args.k)

    print(f"{len(questions)} questions, model {embedder.model}, k={args.k}\n")
    print(f"{'mode':<8} {'recall@' + str(args.k):>9} {'MRR':>6}  misses")
    for mode, r in results.items():
        print(f"{mode:<8} {r[f'recall@{args.k}']:>9.3f} {r['mrr']:>6.3f}  {', '.join(r['misses']) or '-'}")

    if args.check:
        thresholds = json.loads((ROOT / "evals" / "thresholds.json").read_text())
        hybrid = results["hybrid"]
        failures = [
            f"hybrid {metric} {hybrid[metric]} < {minimum}" for metric, minimum in thresholds.items() if hybrid[metric] < minimum
        ]
        if failures:
            print("\nEVAL GATE FAILED: " + "; ".join(failures))
            return 1
        print("\nEval gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
