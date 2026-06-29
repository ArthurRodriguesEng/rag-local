from app.config.database import SessionLocal
from app.repositories.chunk import ChunkRepository
from app.repositories.document import DocumentRepository
from app.services.embedding import EmbeddingService


def main() -> None:
    session = SessionLocal()

    try:
        document_repository = DocumentRepository(session)
        chunk_repository = ChunkRepository(session)
        embedding_service = EmbeddingService()

        document = document_repository.create(
            filename="manual_python.pdf",
        )

        session.flush()

        print("Documento criado na sessão:")
        print(document.id)

        content = "Este é um chunk de teste do manual Python."

        embedding = embedding_service.generate(content)

        print("Embedding gerado:")
        print(len(embedding))

        chunk = chunk_repository.create(
            document_id=document.id,
            content=content,
            embedding=embedding,
        )

        print("Chunk criado na sessão:")
        print(chunk.content)

        session.commit()

        print("Commit realizado com sucesso.")

    except Exception as error:
        session.rollback()
        print("Erro ao salvar dados.")
        print(error)
        raise

    finally:
        session.close()


if __name__ == "__main__":
    main()
