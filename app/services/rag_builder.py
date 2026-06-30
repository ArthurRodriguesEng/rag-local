from dataclasses import dataclass

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


@dataclass(frozen=True)
class RagConfigOverrides:
    """Overrides externos para montar a configuração RAG."""

    limit: int | None = None
    system_prompt: str | None = None
    empty_context_message: str | None = None
    response_mode: str | None = None
    memory_limit: int | None = None
    memory_max_chars: int | None = None


def build_rag_config(
    profile,
    overrides: RagConfigOverrides | None = None,
) -> RagServiceConfig:
    """Monta configuração RAG a partir de perfil e overrides externos."""

    overrides = overrides or RagConfigOverrides()
    selected_limit = (
        overrides.limit
        if overrides.limit is not None
        else profile.retrieval_limit
    )

    return RagServiceConfig(
        retrieval=RetrievalConfig(
            limit=selected_limit,
            candidate_limit=profile.candidate_limit,
            max_distance=settings.RETRIEVAL_MAX_DISTANCE,
            mode=settings.RETRIEVAL_MODE,
            vector_weight=settings.RETRIEVAL_VECTOR_WEIGHT,
            lexical_weight=settings.RETRIEVAL_LEXICAL_WEIGHT,
            term_overlap_weight=settings.RETRIEVAL_TERM_OVERLAP_WEIGHT,
            neighbor_window=settings.RETRIEVAL_NEIGHBOR_WINDOW,
            max_per_document=settings.RETRIEVAL_MAX_PER_DOCUMENT,
            max_per_section=settings.RETRIEVAL_MAX_PER_SECTION,
            enable_query_decomposition=settings.RAG_ENABLE_QUERY_DECOMPOSITION,
            per_subquery_limit=settings.RETRIEVAL_PER_SUBQUERY_LIMIT,
            summary_limit=settings.RETRIEVAL_SUMMARY_LIMIT,
        ),
        prompt=PromptConfig(
            system_prompt=overrides.system_prompt or load_system_prompt(),
            empty_context_message=(
                overrides.empty_context_message
                or settings.RAG_EMPTY_CONTEXT_MESSAGE
            ),
            max_context_chars=profile.max_context_chars,
            response_mode=overrides.response_mode or profile.response_mode,
        ),
        conversation=ConversationConfig(
            memory_limit=(
                overrides.memory_limit
                if overrides.memory_limit is not None
                else profile.memory_limit
            ),
            memory_max_chars=(
                overrides.memory_max_chars
                if overrides.memory_max_chars is not None
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
