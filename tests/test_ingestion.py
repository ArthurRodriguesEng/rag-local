from uuid import uuid4

import pytest

from app.config.settings import settings
from app.models.document import Document
from app.services.ingestion import IngestionService


class FakeSession:
    """Sessão falsa que registra operações transacionais."""

    def __init__(self) -> None:
        self.entities = []
        self.committed = False
        self.rolled_back = False
        self.refreshed = None

    def add(self, entity) -> None:
        self.entities.append(entity)

    def flush(self) -> None:
        for entity in self.entities:
            if isinstance(entity, Document) and entity.id is None:
                entity.id = uuid4()

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def refresh(self, entity) -> None:
        self.refreshed = entity


class FakeLoader:
    """Loader falso com texto controlado pelo teste."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.file_path = None

    def load(self, file_path: str) -> str:
        self.file_path = file_path
        return self.text


class FakeChunker:
    """Chunker falso que retorna chunks pré-definidos."""

    def __init__(self, chunks: list[str]) -> None:
        self.chunks = chunks
        self.text = None

    def split(self, text: str) -> list[str]:
        self.text = text
        return self.chunks


class FakeEmbeddingService:
    """Serviço de embedding falso com falha opcional."""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.inputs = []

    def generate(self, text: str) -> list[float]:
        if self.fail:
            raise RuntimeError("embedding failed")

        self.inputs.append(text)
        return [0.1] * settings.EMBEDDING_DIMENSION


def test_ingest_creates_document_chunks_and_commits() -> None:
    session = FakeSession()
    embedding_service = FakeEmbeddingService()
    service = IngestionService(
        session=session,
        document_loader=FakeLoader("texto completo"),
        text_chunker=FakeChunker(["chunk 1", "chunk 2"]),
        embedding_service=embedding_service,
    )

    document = service.ingest("/tmp/manual_python.txt")

    assert document.filename == "manual_python.txt"
    assert len(session.entities) == 3
    assert embedding_service.inputs == ["chunk 1", "chunk 2"]
    assert session.committed is True
    assert session.rolled_back is False
    assert session.refreshed is document


def test_ingest_rolls_back_when_embedding_fails() -> None:
    session = FakeSession()
    service = IngestionService(
        session=session,
        document_loader=FakeLoader("texto completo"),
        text_chunker=FakeChunker(["chunk 1"]),
        embedding_service=FakeEmbeddingService(fail=True),
    )

    with pytest.raises(RuntimeError, match="embedding failed"):
        service.ingest("/tmp/manual_python.txt")

    assert session.committed is False
    assert session.rolled_back is True


def test_ingest_allows_empty_documents() -> None:
    session = FakeSession()
    service = IngestionService(
        session=session,
        document_loader=FakeLoader(""),
        text_chunker=FakeChunker([]),
        embedding_service=FakeEmbeddingService(),
    )

    document = service.ingest("/tmp/empty.txt")

    assert document.filename == "empty.txt"
    assert len(session.entities) == 1
    assert session.committed is True


def test_ingest_many_creates_each_document() -> None:
    session = FakeSession()
    embedding_service = FakeEmbeddingService()
    service = IngestionService(
        session=session,
        document_loader=FakeLoader("texto completo"),
        text_chunker=FakeChunker(["chunk"]),
        embedding_service=embedding_service,
    )

    documents = service.ingest_many(
        ["/tmp/manual_python.txt", "/tmp/notas.md"]
    )

    assert [document.filename for document in documents] == [
        "manual_python.txt",
        "notas.md",
    ]
    assert len(session.entities) == 4
    assert embedding_service.inputs == ["chunk", "chunk"]
    assert session.committed is True
