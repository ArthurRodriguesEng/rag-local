from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.config.profiles import get_profile
from app.schemas.chat import ChatRequest, ChatResponse, SourceResponse
from app.services.rag import RagService
from app.services.rag_builder import build_rag_config, build_rag_dependencies


router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    session: Session = Depends(get_session),
) -> ChatResponse:
    """Responde uma mensagem usando RAG com histórico de conversa."""

    profile = get_profile(request.profile)
    dependencies = build_rag_dependencies(
        session=session,
        embedding_model=profile.embedding_model,
        chat_provider=profile.chat_provider,
        chat_model=profile.chat_model,
    )
    config = build_rag_config(
        profile=profile,
        limit=request.retrieval_limit,
        response_mode=request.response_mode,
    )
    service = RagService(
        session=session,
        dependencies=dependencies,
        config=config,
    )
    response = service.answer(
        question=request.message,
        limit=request.retrieval_limit,
        conversation_id=(
            UUID(request.conversation_id)
            if request.conversation_id is not None
            else None
        ),
        persist_conversation=True,
    )

    return ChatResponse(
        conversation_id=(
            str(response.conversation_id)
            if response.conversation_id is not None
            else None
        ),
        answer=response.answer,
        sources=[
            SourceResponse(
                document=chunk.document_filename,
                chunk_index=chunk.chunk_index,
                distance=chunk.score,
            )
            for chunk in response.chunks
        ],
    )
