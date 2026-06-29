from pathlib import Path

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.document import Document
from app.repositories.chunk import ChunkRepository
from app.repositories.document import DocumentRepository
from app.services.document_loader import DocumentLoader
from app.services.embedding import EmbeddingService
from app.services.text_chunker import RecursiveTextChunker
from app.utils import logger


class IngestionService:
    """Orquestra o pipeline de ingestão de documentos."""

    def __init__(
        self,
        session: Session,
        document_loader: DocumentLoader | None = None,
        text_chunker: RecursiveTextChunker | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.session = session
        self.document_repository = DocumentRepository(session)
        self.chunk_repository = ChunkRepository(session)
        self.document_loader = document_loader or DocumentLoader()
        self.text_chunker = text_chunker or RecursiveTextChunker(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        self.embedding_service = embedding_service or EmbeddingService()

    def ingest(self, file_path: str) -> Document:
        """Carrega, divide, vetoriza e salva um documento."""

        try:
            text = self.document_loader.load(file_path)
            logger.debug(f"Texto extraído com {len(text)} caracteres.")
            chunks = self.text_chunker.split(text)
            logger.debug(f"Texto dividido em {len(chunks)} chunks.")

            document = self.document_repository.create(
                filename=Path(file_path).name,
            )

            self.session.flush()

            for chunk_index, chunk in enumerate(chunks, start=1):
                embedding = self.embedding_service.generate(chunk)

                self.chunk_repository.create(
                    document_id=document.id,
                    content=chunk,
                    embedding=embedding,
                    chunk_index=chunk_index,
                )

            self.document_repository.commit()
            self.document_repository.refresh(document)
            logger.debug("Transação de ingestão confirmada com commit.")

            return document

        except Exception:
            self.document_repository.rollback()
            logger.warning("Erro na ingestão. Rollback executado.")
            raise
