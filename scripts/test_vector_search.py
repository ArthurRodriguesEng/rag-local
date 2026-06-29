from app.config.database import SessionLocal
from app.repositories.chunk import ChunkRepository
from app.services.embedding import EmbeddingService


def main() -> None:
    question = "Como Python pode ser usado em projetos de inteligência artificial?"
    question = input("Digite sua pergunta: ") or question
    session = SessionLocal()

    try:
        embedding_service = EmbeddingService()
        chunk_repository = ChunkRepository(session)

        question_embedding = embedding_service.generate(question)
        chunks = chunk_repository.search_similar(
            embedding=question_embedding,
            limit=5,
        )

        print(f"Pergunta: {question}")
        print(f"Chunks encontrados: {len(chunks)}")

        for index, chunk in enumerate(chunks, start=1):
            print(f"\n--- Chunk {index} ---")
            print(f"Documento: {chunk.document_id}")
            print(chunk.content)

    finally:
        session.close()


if __name__ == "__main__":
    main()
