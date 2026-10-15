from dataclasses import dataclass

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from ragdocs.config import settings

_HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]


@dataclass(frozen=True)
class Chunk:
    index: int
    heading: str
    content: str

    @property
    def embedding_text(self) -> str:
        # Contextual chunk header: "On-call rotation > Paging policy" disambiguates chunks that read
        # alike out of context ("escalates after 15 minutes" — escalates what?).
        return f"{self.heading}\n\n{self.content}"


def title_of(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def chunk_markdown(markdown: str, title: str, chunk_size: int | None = None, overlap: int | None = None) -> list[Chunk]:
    """Split by headings first, then by size within a section.

    Sections are the natural unit of meaning in docs; size-splitting only applies to sections that are too
    long, so a chunk never straddles two unrelated sections.
    """
    sections = MarkdownHeaderTextSplitter(_HEADERS, strip_headers=True).split_text(markdown)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or settings.chunk_size,
        chunk_overlap=overlap if overlap is not None else settings.chunk_overlap,
    )

    chunks: list[Chunk] = []
    for section in sections:
        path = [section.metadata[k] for k in ("h1", "h2", "h3") if k in section.metadata]
        if not path or path[0] != title:
            path = [title, *[p for p in path if p != title]]
        heading = " > ".join(path)
        for piece in splitter.split_text(section.page_content):
            if piece.strip():
                chunks.append(Chunk(index=len(chunks), heading=heading, content=piece.strip()))
    return chunks
