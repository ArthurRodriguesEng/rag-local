from app.config.database import SessionLocal
from app.config.profiles import get_profile
from app.services.rag import RagService
from app.services.rag_builder import build_rag_config, build_rag_dependencies


def main() -> None:
    question = "Como Python pode ser usado em projetos de inteligência artificial?"
    question = input("Digite sua pergunta: ") or question
    session = SessionLocal()

    try:
        profile = get_profile("fast")
        rag_service = RagService(
            session,
            dependencies=build_rag_dependencies(
                session,
                profile.embedding_model,
                profile.chat_model,
            ),
            config=build_rag_config(profile),
        )
        response = rag_service.answer(
            question=question,
            limit=profile.retrieval_limit,
        )

        print(f"Pergunta: {response.question}")
        print(f"Chunks usados: {len(response.chunks)}")
        print("\nResposta:")
        print(response.answer)

    finally:
        session.close()


if __name__ == "__main__":
    main()
