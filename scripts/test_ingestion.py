from app.config.database import SessionLocal
from app.repositories.chunk import ChunkRepository
from app.services.ingestion import IngestionService


def main() -> None:
    session = SessionLocal()

    try:
        ingestion_service = IngestionService(session)
        chunk_repository = ChunkRepository(session)

        document = ingestion_service.ingest("documents/manual_python.txt")
        chunks = chunk_repository.get_by_document(document.id)

        print("Documento ingerido com sucesso.")
        print(f"ID: {document.id}")
        print(f"Arquivo: {document.filename}")
        print(f"Total de chunks: {len(chunks)}")

        if chunks:
            print(f"Dimensões do primeiro embedding: {len(chunks[0].embedding)}")

    finally:
        session.close()


if __name__ == "__main__":
    main()
