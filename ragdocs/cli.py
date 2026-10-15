"""python -m ragdocs.cli ingest corpus/ [--prune]"""

import argparse
from dataclasses import asdict
from pathlib import Path

from ragdocs.db import connect, migrate
from ragdocs.embeddings import get_embedder
from ragdocs.ingest import ingest, load_directory


def main() -> None:
    parser = argparse.ArgumentParser(prog="ragdocs")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("ingest", help="ingest a directory of .md/.txt files")
    p.add_argument("directory", type=Path)
    p.add_argument("--prune", action="store_true", help="remove indexed documents no longer in the directory")
    args = parser.parse_args()

    with connect() as conn:
        migrate(conn)
        report = ingest(conn, load_directory(args.directory), get_embedder(), prune=args.prune)
    for key, value in asdict(report).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
