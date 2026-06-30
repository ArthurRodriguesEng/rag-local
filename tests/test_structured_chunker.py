from app.services.document_loader import DocumentSegment
from app.services.text_chunker import StructuredTextChunker


def test_structured_chunker_normalizes_text_and_preserves_metadata() -> None:
    chunker = StructuredTextChunker(
        chunk_size=180,
        chunk_overlap=50,
        chunk_min_size=40,
    )
    segments = [
        DocumentSegment(
            content=(
                "1 Introdução\n"
                "Este docu-\n"
                "mento descreve Python.  Ele também fala de RAG.\n\n"
                "2 Método\n"
                "A busca combina embeddings e termos. "
                "Os chunks preservam metadados."
            ),
            page=3,
            start_char=100,
            end_char=260,
        )
    ]

    chunks = chunker.split_segments(segments)

    assert chunks
    assert all(chunk.page == 3 for chunk in chunks)
    assert all(chunk.content_hash for chunk in chunks)
    assert all(len(chunk.content_hash) == 64 for chunk in chunks)
    assert any(chunk.section == "1 Introdução" for chunk in chunks)
    assert any(chunk.section == "2 Método" for chunk in chunks)
    assert "docu-\nmento" not in "\n".join(chunk.content for chunk in chunks)
    assert "documento" in "\n".join(chunk.content for chunk in chunks)


def test_structured_chunker_uses_natural_overlap() -> None:
    chunker = StructuredTextChunker(
        chunk_size=95,
        chunk_overlap=45,
        chunk_min_size=20,
    )
    text = (
        "Primeira sentença sobre Python. "
        "Segunda sentença sobre embeddings. "
        "Terceira sentença sobre busca lexical. "
        "Quarta sentença sobre contexto."
    )

    chunks = chunker.split(text)

    assert len(chunks) >= 2
    assert "Segunda sentença sobre embeddings" in chunks[0]
    assert "Segunda sentença sobre embeddings" in chunks[1]
    assert all(len(chunk) <= 95 for chunk in chunks)
