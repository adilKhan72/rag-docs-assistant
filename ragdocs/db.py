from contextlib import contextmanager
from importlib import resources
from typing import Iterator

import psycopg
from pgvector.psycopg import register_vector

from ragdocs.config import settings


@contextmanager
def connect(url: str | None = None) -> Iterator[psycopg.Connection]:
    with psycopg.connect(url or settings.database_url, autocommit=False) as conn:
        try:
            register_vector(conn)
        except psycopg.ProgrammingError:
            # Fresh database: the vector type appears once migrate() creates the extension.
            conn.rollback()
        yield conn


def migrate(conn: psycopg.Connection) -> None:
    conn.execute(resources.files("ragdocs").joinpath("schema.sql").read_text())
    conn.commit()
    register_vector(conn)
