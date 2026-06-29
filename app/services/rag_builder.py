from sqlalchemy.orm import Session

from app.config.settings import settings
from app.services.chat import ChatService
from app.services.embedding import EmbeddingService
from app.services.rag import (
    ConversationConfig,
    PromptConfig,
    RagDependencies,
    RagServiceConfig,
    RetrievalConfig,
    load_system_prompt,
)


def build_rag_config(
    profile,
    limit: int | None = None,
    system_prompt: str | None = None,
    empty_context_message: str | None = None,
    response_mode: str | None = None,
    memory_limit: int | None = None,
    memory_max_chars: int | None = None,
) -> RagServiceConfig:
    """Monta configuração RAG a partir de perfil e overrides externos."""

    selected_limit = limit if limit is not None else profile.retrieval_limit

    return RagServiceConfig(
        retrieval=RetrievalConfig(
            limit=selected_limit,
            candidate_limit=profile.candidate_limit,
            max_distance=settings.RETRIEVAL_MAX_DISTANCE,
        ),
        prompt=PromptConfig(
            system_prompt=system_prompt or load_system_prompt(),
            empty_context_message=(
                empty_context_message or settings.RAG_EMPTY_CONTEXT_MESSAGE
            ),
            max_context_chars=profile.max_context_chars,
            response_mode=response_mode or profile.response_mode,
        ),
        conversation=ConversationConfig(
            memory_limit=(
                memory_limit
                if memory_limit is not None
                else profile.memory_limit
            ),
            memory_max_chars=(
                memory_max_chars
                if memory_max_chars is not None
                else profile.memory_max_chars
            ),
        ),
    )


def build_rag_dependencies(
    session: Session,
    embedding_model: str,
    chat_model: str,
) -> RagDependencies:
    """Monta dependências RAG concretas para a camada de entrada."""

    return RagDependencies.from_overrides(
        session=session,
        embedding_service=EmbeddingService(embedding_model=embedding_model),
        chat_service=ChatService.from_overrides(
            chat_model=chat_model,
        ),
    )
