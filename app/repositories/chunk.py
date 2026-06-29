from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.repositories.base import BaseRepository


@dataclass(frozen=True)
class RetrievedChunk:
    """Chunk recuperado junto com informações da busca vetorial."""

    chunk: Chunk
    score: float

    @property
    def content(self) -> str:
        """Atalho para manter o uso do conteúdo simples."""

        return self.chunk.content

    @property
    def document_filename(self) -> str:
        """Nome do documento de origem."""

        return self.chunk.document.filename

    @property
    def chunk_index(self) -> int:
        """Posição do chunk dentro do documento."""

        return self.chunk.chunk_index


class ChunkRepository(BaseRepository):
    """Repository responsável pelos chunks."""

    def __init__(self, session: Session):
        super().__init__(session)

    def create(
        self,
        document_id: UUID,
        content: str,
        embedding: list[float],
        chunk_index: int = 0,
    ) -> Chunk:
        """Cria um novo chunk."""

        chunk = Chunk(
            document_id=document_id,
            content=content,
            embedding=embedding,
            chunk_index=chunk_index,
            char_count=len(content),
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

    def search_similar(
        self,
        embedding: list[float],
        limit: int = 5,
        max_distance: float | None = None,
    ) -> list[RetrievedChunk]:
        """Busca chunks mais próximos do embedding informado."""

        distance_expression = Chunk.embedding.cosine_distance(embedding)
        distance = distance_expression.label("score")
        statement = (
            select(Chunk, distance)
            .options(selectinload(Chunk.document))
            .order_by(distance_expression)
            .limit(limit)
        )

        rows = self.session.execute(statement).all()
        results = [
            RetrievedChunk(
                chunk=chunk,
                score=float(score),
            )
            for chunk, score in rows
            if max_distance is None or float(score) <= max_distance
        ]

        return results
