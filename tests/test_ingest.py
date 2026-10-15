from pathlib import Path

from ragdocs.ingest import SourceDocument, ingest, load_directory

CORPUS = Path(__file__).resolve().parents[1] / "corpus"


def _count(conn, sql, *args):
    return conn.execute(sql, args).fetchone()[0]


def test_ingesting_the_corpus_creates_documents_and_searchable_chunks(db, embedder):
    docs = load_directory(CORPUS)

    report = ingest(db, docs, embedder)

    assert len(report.added) == len(docs) == 11
    assert report.chunks_written == _count(db, "SELECT count(*) FROM chunks") > 30
    assert _count(db, "SELECT count(*) FROM chunks WHERE embedding_model = %s", embedder.model) == report.chunks_written
    # The generated tsvector is populated and weighted: the heading word matches.
    assert _count(db, "SELECT count(*) FROM chunks WHERE tsv @@ websearch_to_tsquery('english', 'canary')") >= 1
    title = db.execute("SELECT title FROM documents WHERE source = 'on-call.md'").fetchone()[0]
    assert title == "On-call rotation"


def test_reingesting_unchanged_documents_is_a_no_op(db, embedder):
    docs = load_directory(CORPUS)
    ingest(db, docs, embedder)
    ids_before = db.execute("SELECT array_agg(id ORDER BY id) FROM chunks").fetchone()[0]

    report = ingest(db, docs, embedder)

    assert report.unchanged == [d.source for d in docs]
    assert report.chunks_written == 0
    assert db.execute("SELECT array_agg(id ORDER BY id) FROM chunks").fetchone()[0] == ids_before


def test_a_changed_document_is_rechunked_in_place(db, embedder):
    ingest(db, [SourceDocument("a.md", "# A\n\n## One\nold text")], embedder)

    report = ingest(db, [SourceDocument("a.md", "# A\n\n## One\nnew text\n\n## Two\nmore")], embedder)

    assert report.updated == ["a.md"]
    contents = [r[0] for r in db.execute("SELECT content FROM chunks ORDER BY chunk_index")]
    assert contents == ["new text", "more"]
    assert _count(db, "SELECT count(*) FROM documents") == 1


def test_switching_embedding_model_forces_reembedding(db, embedder):
    doc = SourceDocument("a.md", "# A\n\ntext")
    ingest(db, [doc], embedder)
    embedder.model = "another-model"

    report = ingest(db, [doc], embedder)

    assert report.updated == ["a.md"]
    assert db.execute("SELECT DISTINCT embedding_model FROM chunks").fetchall() == [("another-model",)]


def test_prune_mirrors_the_given_set(db, embedder):
    ingest(db, [SourceDocument("a.md", "# A\n\nx"), SourceDocument("b.md", "# B\n\ny")], embedder)

    report = ingest(db, [SourceDocument("a.md", "# A\n\nx")], embedder, prune=True)

    assert report.removed == ["b.md"]
    assert _count(db, "SELECT count(*) FROM chunks c JOIN documents d ON d.id = c.document_id WHERE d.source = 'b.md'") == 0
