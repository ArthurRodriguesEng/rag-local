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
