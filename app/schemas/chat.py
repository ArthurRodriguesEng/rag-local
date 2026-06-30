from pydantic import BaseModel


class SourceResponse(BaseModel):
    """Fonte usada para compor uma resposta do RAG."""

    document: str
    chunk_index: int
    distance: float
    page: int | None = None
    section: str | None = None
    score: float | None = None
    vector_distance: float | None = None
    lexical_score: float | None = None
    chunk_type: str | None = None
    subquery: str | None = None


class ChatRequest(BaseModel):
    """Payload de entrada do endpoint de chat."""

    message: str
    conversation_id: str | None = None
    profile: str | None = None
    retrieval_limit: int | None = None
    response_mode: str | None = None
    memory_limit: int | None = None
    memory_max_chars: int | None = None


class ChatResponse(BaseModel):
    """Resposta HTTP do chat RAG."""

    conversation_id: str | None
    answer: str
    sources: list[SourceResponse]
