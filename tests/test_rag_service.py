from types import SimpleNamespace

from app.config.settings import settings
from app.repositories.chunk import RetrievedChunk
from app.services.rag import RagDependencies, RagService


class FakeEmbeddingService:
    """Serviço de embedding falso que registra as perguntas recebidas."""

    def __init__(self) -> None:
        self.inputs = []

    def generate(self, text: str) -> list[float]:
        self.inputs.append(text)
        return [0.2] * settings.EMBEDDING_DIMENSION


class FakeChunkRepository:
    """Repositório falso que registra os parâmetros da busca vetorial."""

    def __init__(self, chunks: list[object]) -> None:
        self.chunks = chunks
        self.embedding = None
        self.limit = None
        self.max_distance = None

    def search_similar(
        self,
        embedding: list[float],
        limit: int = 5,
        max_distance: float | None = None,
    ) -> list[object]:
        self.embedding = embedding
        self.limit = limit
        self.max_distance = max_distance
        return self.chunks


class FakeChatService:
    """Serviço de chat falso que registra o prompt final."""

    def __init__(self) -> None:
        self.prompt = None

    def generate(self, prompt: str) -> str:
        self.prompt = prompt
        return "Resposta baseada nos documentos."


def make_service(
    embedding_service: FakeEmbeddingService,
    chunk_repository: FakeChunkRepository,
    chat_service: FakeChatService,
) -> RagService:
    """Cria o RagService com dependências falsas."""

    return RagService(
        session=object(),
        dependencies=RagDependencies(
            embedding_service=embedding_service,
            chunk_repository=chunk_repository,
            conversation_repository=object(),
            message_repository=object(),
            chat_service=chat_service,
        ),
    )


def test_answer_searches_chunks_and_generates_response() -> None:
    raw_chunks = [
        SimpleNamespace(
            content="Python é usado em IA.",
            chunk_index=1,
            document=SimpleNamespace(filename="manual.txt"),
        ),
        SimpleNamespace(
            content="RAG combina busca e geração.",
            chunk_index=2,
            document=SimpleNamespace(filename="manual.txt"),
        ),
    ]
    chunks = [
        RetrievedChunk(chunk=raw_chunks[0], score=0.12),
        RetrievedChunk(chunk=raw_chunks[1], score=0.22),
    ]
    embedding_service = FakeEmbeddingService()
    chunk_repository = FakeChunkRepository(chunks)
    chat_service = FakeChatService()
    service = make_service(
        embedding_service=embedding_service,
        chunk_repository=chunk_repository,
        chat_service=chat_service,
    )

    response = service.answer(
        question="Como Python é usado em IA?",
        limit=2,
    )

    assert embedding_service.inputs == ["Como Python é usado em IA?"]
    assert chunk_repository.embedding == [0.2] * settings.EMBEDDING_DIMENSION
    assert chunk_repository.limit == settings.RETRIEVAL_CANDIDATE_LIMIT
    assert "Python é usado em IA." in chat_service.prompt
    assert "RAG combina busca e geração." in chat_service.prompt
    assert "Documento: manual.txt" in chat_service.prompt
    assert "Como Python é usado em IA?" in chat_service.prompt
    assert response.answer == "Resposta baseada nos documentos."
    assert response.chunks == chunks


def test_prompt_handles_empty_context() -> None:
    service = make_service(
        embedding_service=FakeEmbeddingService(),
        chunk_repository=FakeChunkRepository([]),
        chat_service=FakeChatService(),
    )

    response = service.answer("Pergunta sem contexto")

    assert "Nenhum contexto encontrado." in service.chat_service.prompt
    assert not response.chunks


def test_capability_question_does_not_search_documents() -> None:
    embedding_service = FakeEmbeddingService()
    chunk_repository = FakeChunkRepository([])
    chat_service = FakeChatService()
    service = make_service(
        embedding_service=embedding_service,
        chunk_repository=chunk_repository,
        chat_service=chat_service,
    )

    response = service.answer("O que você faz?")

    assert not embedding_service.inputs
    assert chunk_repository.embedding is None
    assert chat_service.prompt is None
    assert "assistente RAG interno" in response.answer
    assert not response.chunks
