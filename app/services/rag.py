from dataclasses import dataclass
from pathlib import Path
from unicodedata import normalize
from uuid import UUID

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.message import Message
from app.repositories.chunk import ChunkRepository, RetrievedChunk
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.services.chat import ChatService
from app.services.embedding import EmbeddingService
from app.utils import logger


def load_system_prompt() -> str:
    """Carrega prompt de arquivo, com fallback para configuração."""

    prompt_path = Path(settings.RAG_PROMPT_PATH)

    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8").strip()

    return settings.RAG_SYSTEM_PROMPT


@dataclass
class RagResponse:
    """Resposta final do RAG junto com os chunks usados como contexto."""

    question: str
    answer: str
    chunks: list[RetrievedChunk]
    conversation_id: UUID | None = None


@dataclass(frozen=True)
class RetrievalConfig:
    """Parâmetros de recuperação vetorial."""

    limit: int
    candidate_limit: int
    max_distance: float | None


@dataclass(frozen=True)
class PromptConfig:
    """Parâmetros de montagem do prompt final."""

    system_prompt: str
    empty_context_message: str
    max_context_chars: int
    response_mode: str


@dataclass(frozen=True)
class ConversationConfig:
    """Parâmetros da memória recente do agente."""

    memory_limit: int
    memory_max_chars: int


@dataclass(frozen=True)
class RagServiceConfig:
    """Configuração de aplicação do serviço RAG."""

    retrieval: RetrievalConfig
    prompt: PromptConfig
    conversation: ConversationConfig

    @classmethod
    def from_settings(cls, system_prompt: str) -> "RagServiceConfig":
        """Cria a configuração padrão a partir das settings da aplicação."""

        return cls(
            retrieval=RetrievalConfig(
                limit=settings.RETRIEVAL_LIMIT,
                candidate_limit=settings.RETRIEVAL_CANDIDATE_LIMIT,
                max_distance=settings.RETRIEVAL_MAX_DISTANCE,
            ),
            prompt=PromptConfig(
                system_prompt=system_prompt,
                empty_context_message=settings.RAG_EMPTY_CONTEXT_MESSAGE,
                max_context_chars=settings.RAG_MAX_CONTEXT_CHARS,
                response_mode=settings.RAG_RESPONSE_MODE,
            ),
            conversation=ConversationConfig(
                memory_limit=settings.RAG_MEMORY_LIMIT,
                memory_max_chars=settings.RAG_MEMORY_MAX_CHARS,
            ),
        )


@dataclass
class RagDependencies:
    """Dependências externas usadas pela orquestração RAG."""

    embedding_service: EmbeddingService
    chunk_repository: ChunkRepository
    conversation_repository: ConversationRepository
    message_repository: MessageRepository
    chat_service: ChatService

    @classmethod
    def from_session(cls, session: Session) -> "RagDependencies":
        """Instancia dependências padrão com a sessão informada."""

        return cls.from_overrides(session=session)

    @classmethod
    def from_overrides(
        cls,
        session: Session,
        embedding_service: EmbeddingService | None = None,
        chat_service: ChatService | None = None,
    ) -> "RagDependencies":
        """Instancia dependências padrão permitindo trocar portas externas."""

        return cls(
            embedding_service=embedding_service or EmbeddingService(),
            chunk_repository=ChunkRepository(session),
            conversation_repository=ConversationRepository(session),
            message_repository=MessageRepository(session),
            chat_service=chat_service or ChatService(),
        )


class RagService:
    """Orquestra pergunta, busca vetorial e resposta final."""

    def __init__(
        self,
        session: Session,
        dependencies: RagDependencies | None = None,
        config: RagServiceConfig | None = None,
    ) -> None:
        self.session = session
        self.dependencies = dependencies or RagDependencies.from_session(session)
        self.config = config or RagServiceConfig.from_settings(
            system_prompt=load_system_prompt(),
        )

    @property
    def chat_service(self) -> ChatService:
        """Expõe o serviço de chat para inspeção em testes."""

        return self.dependencies.chat_service

    def answer(
        self,
        question: str,
        limit: int | None = None,
        conversation_id: UUID | None = None,
        persist_conversation: bool = False,
    ) -> RagResponse:
        """Responde uma pergunta usando os chunks mais relevantes."""

        search_limit = limit if limit is not None else self.config.retrieval.limit
        candidate_limit = max(
            search_limit,
            self.config.retrieval.candidate_limit,
        )
        conversation = None
        history: list[Message] = []

        if persist_conversation:
            conversation = self._get_or_create_conversation(
                conversation_id=conversation_id,
                question=question,
            )
            self.session.flush()
            history = self.dependencies.message_repository.list_by_conversation(
                conversation_id=conversation.id,
                limit=self.config.conversation.memory_limit,
            )

        if self._is_assistant_capability_question(question):
            answer = self._build_assistant_capability_answer()
            self._save_conversation_messages(
                conversation_id=conversation.id if conversation else None,
                question=question,
                answer=answer,
            )

            return RagResponse(
                question=question,
                answer=answer,
                chunks=[],
                conversation_id=(
                    conversation.id if conversation is not None else None
                ),
            )

        question_embedding = self.dependencies.embedding_service.generate(question)
        chunks = self.dependencies.chunk_repository.search_similar(
            embedding=question_embedding,
            limit=candidate_limit,
            max_distance=self.config.retrieval.max_distance,
        )
        chunks = self._select_context_chunks(
            chunks=chunks,
            limit=search_limit,
        )
        logger.debug(f"Busca vetorial retornou {len(chunks)} chunks.")
        prompt = self._build_prompt(
            question=question,
            chunks=chunks,
            history=history,
        )
        logger.debug(f"Prompt final montado com {len(prompt)} caracteres.")
        answer = self.dependencies.chat_service.generate(prompt)

        self._save_conversation_messages(
            conversation_id=conversation.id if conversation else None,
            question=question,
            answer=answer,
        )

        return RagResponse(
            question=question,
            answer=answer,
            chunks=chunks,
            conversation_id=conversation.id if conversation is not None else None,
        )

    def _build_prompt(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        history: list[Message] | None = None,
    ) -> str:
        """Monta o prompt com instruções, contexto e pergunta."""

        context = self._format_context(chunks)
        formatted_history = self._format_history(history or [])

        return (
            f"{self.config.prompt.system_prompt}\n"
            "Se o contexto não tiver informação suficiente, responda "
            f"exatamente: {self.config.prompt.empty_context_message}\n\n"
            f"Modo de resposta: {self.config.prompt.response_mode}\n\n"
            f"Memória recente da conversa:\n{formatted_history}\n\n"
            f"Contexto:\n{context}\n\n"
            f"Pergunta:\n{question}\n\n"
            "Resposta:"
        )

    def _format_context(self, chunks: list[RetrievedChunk]) -> str:
        """Formata chunks recuperados como blocos numerados."""

        if not chunks:
            return "Nenhum contexto encontrado."

        blocks = []
        total_chars = 0

        for index, retrieved in enumerate(chunks, start=1):
            block = (
                f"[{index}] Documento: {retrieved.document_filename}; "
                f"trecho: {retrieved.chunk_index}; "
                f"distância: {retrieved.score:.4f}\n"
                f"{retrieved.content}"
            )

            if total_chars + len(block) > self.config.prompt.max_context_chars:
                break

            blocks.append(block)
            total_chars += len(block)

        if not blocks:
            return "Nenhum contexto encontrado."

        return "\n\n".join(blocks)

    def _format_history(self, messages: list[Message]) -> str:
        """Formata a memória recente da conversa."""

        if not messages:
            return "Sem histórico anterior."

        lines = []
        total_chars = 0

        for message in messages:
            line = f"{message.role}: {message.content}"

            if (
                total_chars + len(line)
                > self.config.conversation.memory_max_chars
            ):
                break

            lines.append(line)
            total_chars += len(line)

        return "\n".join(lines)

    def _select_context_chunks(
        self,
        chunks: list[RetrievedChunk],
        limit: int,
    ) -> list[RetrievedChunk]:
        """Remove duplicados e limita os chunks enviados ao prompt."""

        selected = []
        seen_contents = set()

        for chunk in chunks:
            content_key = chunk.content.strip()

            if content_key in seen_contents:
                continue

            seen_contents.add(content_key)
            selected.append(chunk)

            if len(selected) >= limit:
                break

        return selected

    def _get_or_create_conversation(
        self,
        conversation_id: UUID | None,
        question: str,
    ):
        """Retorna uma conversa existente ou cria uma nova."""

        if conversation_id is not None:
            conversation = self.dependencies.conversation_repository.get_by_id(
                conversation_id
            )

            if conversation is None:
                raise ValueError(f"Conversa não encontrada: {conversation_id}")

            return conversation

        title = question[:80]
        return self.dependencies.conversation_repository.create(title=title)

    def _save_conversation_messages(
        self,
        conversation_id: UUID | None,
        question: str,
        answer: str,
    ) -> None:
        """Persiste pergunta e resposta quando houver conversa ativa."""

        if conversation_id is None:
            return

        self.dependencies.message_repository.create(
            conversation_id=conversation_id,
            role="user",
            content=question,
        )
        self.dependencies.message_repository.create(
            conversation_id=conversation_id,
            role="assistant",
            content=answer,
        )
        self.session.commit()

    def _is_assistant_capability_question(self, question: str) -> bool:
        """Identifica saudações e perguntas sobre o próprio assistente."""

        normalized_question = self._normalize_question(question)

        greetings = {
            "oi",
            "ola",
            "olá",
            "bom dia",
            "boa tarde",
            "boa noite",
        }

        if normalized_question in greetings:
            return True

        capability_patterns = [
            "o que voce faz",
            "quem e voce",
            "sobre o que voce fala",
            "como voce funciona",
            "para que voce serve",
        ]

        return any(
            pattern in normalized_question
            for pattern in capability_patterns
        )

    def _build_assistant_capability_answer(self) -> str:
        """Resposta fixa para explicar o papel do assistente."""

        return (
            "Sou um assistente RAG interno para consulta de documentos. "
            "Eu busco trechos relevantes nos arquivos ingeridos, uso esses "
            "trechos como contexto e respondo com base neles. Posso ajudar a "
            "resumir documentos, localizar autores, explicar resultados, "
            "comparar seções e extrair insights, sempre indicando as fontes "
            "quando a pergunta exigir consulta à base."
        )

    def _normalize_question(self, question: str) -> str:
        """Normaliza texto para regras simples de intenção."""

        normalized = normalize("NFKD", question.lower())
        return "".join(
            character
            for character in normalized
            if not ord(character) >= 128
        ).strip(" ?!.,;:")

    def _load_system_prompt(self) -> str:
        """Carrega prompt de arquivo, com fallback para configuração."""

        return load_system_prompt()
