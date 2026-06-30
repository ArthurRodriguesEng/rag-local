from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.config.settings import settings
from app.repositories.chunk import ChunkRepository


class FakeExecuteResult:
    """Resultado falso de uma execução SQLAlchemy."""

    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def all(self):
        return self.rows


class FakeSession:
    """Sessão falsa que registra a statement executada."""

    def __init__(self, rows: list[object]) -> None:
        self.rows = rows
        self.statement = None

    def execute(self, statement):
        self.statement = statement
        return FakeExecuteResult(self.rows)


class SequentialFakeSession:
    """Sessão falsa que retorna lotes de linhas em sequência."""

    def __init__(self, row_batches: list[list[object]]) -> None:
        self.row_batches = row_batches
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)
        return FakeExecuteResult(self.row_batches.pop(0))


def test_search_similar_orders_by_cosine_distance() -> None:
    chunks = [object(), object()]
    rows = [(chunks[0], 0.12), (chunks[1], 0.24)]
    session = FakeSession(rows)
    repository = ChunkRepository(session)

    result = repository.search_similar(
        embedding=[0.1] * settings.EMBEDDING_DIMENSION,
        limit=5,
    )

    compiled = str(
        session.statement.compile(
            dialect=postgresql.dialect(),
        )
    )

    assert [item.chunk for item in result] == chunks
    assert [item.score for item in result] == [0.12, 0.24]
    assert "ORDER BY chunks.embedding <=>" in compiled
    assert "LIMIT" in compiled


def test_search_hybrid_merges_vector_and_lexical_scores() -> None:
    vector_chunk = SimpleNamespace(
        id=uuid4(),
        content="Python usa embeddings em sistemas RAG.",
        chunk_index=1,
        content_hash=None,
        page=2,
        section="Python",
        document=SimpleNamespace(filename="manual.txt"),
    )
    lexical_chunk = SimpleNamespace(
        id=uuid4(),
        content="Busca lexical usa termos da pergunta.",
        chunk_index=2,
        content_hash=None,
        page=3,
        section="Busca",
        document=SimpleNamespace(filename="manual.txt"),
    )
    session = SequentialFakeSession(
        row_batches=[
            [(vector_chunk, 0.20)],
            [(lexical_chunk, 0.80)],
        ]
    )
    repository = ChunkRepository(session)

    result = repository.search_hybrid(
        query="Como a busca lexical usa termos?",
        embedding=[0.1] * settings.EMBEDDING_DIMENSION,
        limit=2,
        vector_limit=1,
        lexical_limit=1,
    )

    lexical_statement = str(
        session.statements[1].compile(
            dialect=postgresql.dialect(),
        )
    )

    assert len(result) == 2
    assert result[0].chunk is vector_chunk
    assert result[0].vector_distance == 0.20
    assert result[1].chunk is lexical_chunk
    assert result[1].lexical_score == 0.80
    assert "to_tsvector" in lexical_statement
    assert "@@" in lexical_statement
