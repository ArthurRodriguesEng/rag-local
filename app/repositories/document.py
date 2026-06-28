from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository):
    """Repository responsável pelos documentos."""

    def __init__(self, session: Session):
        super().__init__(session)

    def create(self, filename: str) -> Document:
        """Cria um novo documento."""

        document = Document(filename=filename)

        self.add(document)

        return document

    def get_by_id(self, document_id: UUID) -> Document | None:
        """Busca um documento pelo ID."""

        statement = select(Document).where(Document.id == document_id)

        return self.scalar(statement)

    def list_all(self) -> list[Document]:
        """Lista todos os documentos."""

        statement = select(Document)

        return list(self.scalars(statement))
