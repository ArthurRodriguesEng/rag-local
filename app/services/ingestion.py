from pathlib import Path

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.document import Document
from app.repositories.chunk import ChunkRepository
from app.repositories.document import DocumentRepository
from app.services.document_loader import DocumentLoader
from app.services.embedding import EmbeddingService
from app.services.summarization import SummaryService
from app.services.text_chunker import RecursiveTextChunker, StructuredTextChunker
from app.utils import logger


class IngestionService:
    """Orquestra o pipeline de ingestão de documentos."""

    def __init__(
        self,
        session: Session,
        document_loader: DocumentLoader | None = None,
        text_chunker: RecursiveTextChunker | StructuredTextChunker | None = None,
        embedding_service: EmbeddingService | None = None,
        summary_service: SummaryService | None = None,
    ) -> None:
        self.session = session
        self.document_repository = DocumentRepository(session)
        self.chunk_repository = ChunkRepository(session)
        self.document_loader = document_loader or DocumentLoader()
        self.text_chunker = text_chunker or StructuredTextChunker(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            chunk_min_size=settings.CHUNK_MIN_SIZE,
        )
        self.embedding_service = embedding_service or EmbeddingService()
        self.summary_service = summary_service or (
            SummaryService()
            if settings.RAG_ENABLE_SECTION_SUMMARIES
            else None
        )

    def ingest(self, file_path: str) -> Document:
        """Carrega, divide, vetoriza e salva um documento."""

        try:
            chunks = self._load_chunks(file_path)
            logger.debug(f"Texto dividido em {len(chunks)} chunks.")

            document = self.document_repository.create(
                filename=Path(file_path).name,
            )

            self.session.flush()

            chunk_index = 0

            for chunk in chunks:
                chunk_index += 1
                content = chunk.content if hasattr(chunk, "content") else chunk
                embedding = self.embedding_service.generate(content)

                self.chunk_repository.create(
                    document_id=document.id,
                    content=content,
                    embedding=embedding,
                    chunk_index=chunk_index,
                    page=getattr(chunk, "page", None),
                    section=getattr(chunk, "section", None),
                    start_char=getattr(chunk, "start_char", None),
                    end_char=getattr(chunk, "end_char", None),
                    content_hash=getattr(chunk, "content_hash", None),
                    chunk_type=getattr(chunk, "chunk_type", "content"),
                )

            for summary in self._build_summary_chunks(
                chunks=chunks,
                document_name=Path(file_path).name,
            ):
                chunk_index += 1
                embedding = self.embedding_service.generate(summary.content)
                self.chunk_repository.create(
                    document_id=document.id,
                    content=summary.content,
                    embedding=embedding,
                    chunk_index=chunk_index,
                    page=summary.page,
                    section=summary.section,
                    start_char=summary.start_char,
                    end_char=summary.end_char,
                    chunk_type=summary.chunk_type,
                )

            self.document_repository.commit()
            self.document_repository.refresh(document)
            logger.debug("Transação de ingestão confirmada com commit.")

            return document

        except Exception:
            self.document_repository.rollback()
            logger.warning("Erro na ingestão. Rollback executado.")
            raise

    def _load_chunks(self, file_path: str):
        """Carrega chunks usando a interface estruturada quando disponível."""

        if hasattr(self.document_loader, "load_segments") and hasattr(
            self.text_chunker,
            "split_segments",
        ):
            segments = self.document_loader.load_segments(file_path)
            total_chars = sum(len(segment.content) for segment in segments)
            logger.debug(f"Texto extraído com {total_chars} caracteres.")
            return self.text_chunker.split_segments(segments)

        text = self.document_loader.load(file_path)
        logger.debug(f"Texto extraído com {len(text)} caracteres.")
        return self.text_chunker.split(text)

    def _build_summary_chunks(self, chunks, document_name: str):
        """Gera resumos apenas para chunks estruturados."""

        if self.summary_service is None or not chunks:
            return []

        if not all(hasattr(chunk, "content_hash") for chunk in chunks):
            return []

        return self.summary_service.summarize(
            chunks=chunks,
            document_name=document_name,
        )
