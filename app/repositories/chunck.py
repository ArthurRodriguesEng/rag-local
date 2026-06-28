from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.repositories.base import BaseRepository


class ChunkRepository(BaseRepository):
    """Repository responsável pelos chunks."""

    def __init__(self, session: Session):
        super().__init__(session)

    def create(
        self,
        document_id: UUID,
        content: str,
        embedding: list[float],
    ) -> Chunk:
        """Cria um novo chunk."""

        chunk = Chunk(
            document_id=document_id,
            content=content,
            embedding=embedding,
        )

        self.add(chunk)

        return chunk

    def get_by_id(self, chunk_id: UUID) -> Chunk | None:
        """Busca um chunk pelo ID."""

        statement = select(Chunk).where(Chunk.id == chunk_id)

        return self.scalar(statement)

    def get_by_document(self, document_id: UUID) -> list[Chunk]:
        """Retorna todos os chunks de um documento."""

        statement = select(Chunk).where(Chunk.document_id == document_id)

        return list(self.scalars(statement))

    def count(self) -> int:
        """Retorna a quantidade de chunks."""

        statement = select(func.count()).select_from(Chunk)

        return self.scalar(statement)
