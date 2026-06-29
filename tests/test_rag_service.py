from types import SimpleNamespace
from uuid import uuid4

from app.config.settings import settings
from app.repositories.chunk import RetrievedChunk
from app.services.rag import (
    ConversationConfig,
    PromptConfig,
    RagDependencies,
    RagService,
    RagServiceConfig,
    RetrievalConfig,
)


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


class FakeSession:
    """Sessão falsa para fluxos com conversa persistida."""

    def __init__(self) -> None:
        self.committed = False

    def flush(self) -> None:
        return None

    def commit(self) -> None:
        self.committed = True


class FakeConversationRepository:
    """Repositório falso que cria uma conversa estável."""

    def __init__(self) -> None:
        self.conversation = SimpleNamespace(id=uuid4())

    def create(self, title: str):
        self.conversation.title = title
        return self.conversation

    def get_by_id(self, conversation_id):
        return SimpleNamespace(id=conversation_id)


class FakeMessageRepository:
    """Repositório falso que registra limite e mensagens salvas."""

    def __init__(self, messages: list[object]) -> None:
        self.messages = messages
        self.limit = None
        self.saved = []

    def list_by_conversation(self, conversation_id, limit: int):
        self.limit = limit
        return self.messages[:limit]

    def create(self, conversation_id, role: str, content: str) -> None:
        self.saved.append(
            {
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
            }
        )


def make_service(
    embedding_service: FakeEmbeddingService,
    chunk_repository: FakeChunkRepository,
    chat_service: FakeChatService,
    session=None,
    conversation_repository=None,
    message_repository=None,
    config=None,
) -> RagService:
    """Cria o RagService com dependências falsas."""

    return RagService(
        session=session or object(),
        dependencies=RagDependencies(
            embedding_service=embedding_service,
            chunk_repository=chunk_repository,
            conversation_repository=conversation_repository or object(),
            message_repository=message_repository or object(),
            chat_service=chat_service,
        ),
        config=config,
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


def test_agent_memory_limit_and_char_budget_are_applied() -> None:
    messages = [
        SimpleNamespace(role="user", content="pergunta anterior curta"),
        SimpleNamespace(role="assistant", content="resposta anterior curta"),
        SimpleNamespace(role="user", content="mensagem que excederia o limite"),
    ]
    message_repository = FakeMessageRepository(messages)
    chat_service = FakeChatService()
    config = RagServiceConfig(
        retrieval=RetrievalConfig(
            limit=1,
            candidate_limit=1,
            max_distance=None,
        ),
        prompt=PromptConfig(
            system_prompt="Prompt local",
            empty_context_message="Sem contexto",
            max_context_chars=1000,
            response_mode="concise",
        ),
        conversation=ConversationConfig(
            memory_limit=3,
            memory_max_chars=80,
        ),
    )
    service = make_service(
        embedding_service=FakeEmbeddingService(),
        chunk_repository=FakeChunkRepository([]),
        chat_service=chat_service,
        session=FakeSession(),
        conversation_repository=FakeConversationRepository(),
        message_repository=message_repository,
        config=config,
    )

    service.answer(
        question="Nova pergunta",
        persist_conversation=True,
    )

    assert message_repository.limit == 3
    assert "Memória recente da conversa:" in chat_service.prompt
    assert "pergunta anterior curta" in chat_service.prompt
    assert "resposta anterior curta" in chat_service.prompt
    assert "mensagem que excederia o limite" not in chat_service.prompt
