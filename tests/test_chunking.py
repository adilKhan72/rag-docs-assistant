from ragdocs.chunking import chunk_markdown, title_of

DOC = """# On-call rotation

Intro paragraph about the rotation.

## Paging policy
Pages escalate after 5 minutes.

### Escalation
Then to the manager after 15 minutes.

## Compensation
USD 150 per week.
"""


def test_chunks_follow_sections_with_a_heading_breadcrumb():
    chunks = chunk_markdown(DOC, "On-call rotation")

    assert [c.heading for c in chunks] == [
        "On-call rotation",
        "On-call rotation > Paging policy",
        "On-call rotation > Paging policy > Escalation",
        "On-call rotation > Compensation",
    ]
    assert chunks[1].content == "Pages escalate after 5 minutes."
    assert [c.index for c in chunks] == [0, 1, 2, 3]


def test_a_chunk_never_straddles_two_sections():
    chunks = chunk_markdown(DOC, "On-call rotation")

    assert all(not ("5 minutes" in c.content and "USD 150" in c.content) for c in chunks)


def test_long_sections_are_split_by_size_with_overlap():
    body = " ".join(f"sentence{i} about policies." for i in range(200))
    chunks = chunk_markdown(f"# Big\n\n## Section\n{body}", "Big", chunk_size=300, overlap=50)

    assert len(chunks) > 3
    assert all(len(c.content) <= 300 for c in chunks)
    assert all(c.heading == "Big > Section" for c in chunks)


def test_embedding_text_carries_the_heading_for_context():
    chunk = chunk_markdown(DOC, "On-call rotation")[1]

    assert chunk.embedding_text.startswith("On-call rotation > Paging policy\n\n")


def test_title_comes_from_the_first_h1_or_falls_back():
    assert title_of(DOC, "x") == "On-call rotation"
    assert title_of("no heading here", "Leave Policy") == "Leave Policy"
