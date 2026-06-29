from pydantic import BaseModel


class SourceResponse(BaseModel):
    """Fonte usada para compor uma resposta do RAG."""

    document: str
    chunk_index: int
    distance: float


class ChatRequest(BaseModel):
    """Payload de entrada do endpoint de chat."""

    message: str
    conversation_id: str | None = None
    profile: str | None = None
    retrieval_limit: int | None = None
    response_mode: str | None = None


class ChatResponse(BaseModel):
    """Resposta HTTP do chat RAG."""

    conversation_id: str | None
    answer: str
    sources: list[SourceResponse]
