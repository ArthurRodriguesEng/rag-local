import re
from dataclasses import dataclass
from pathlib import Path
from unicodedata import normalize
from uuid import UUID

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.message import Message
from app.repositories.chunk import (
    ChunkRepository,
    HybridSearchOptions,
    HybridSearchWeights,
    RetrievedChunk,
)
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
class QuerySubtask:
    """Subconsulta interna para perguntas compostas."""

    label: str
    query: str


@dataclass(frozen=True)
class RetrievalConfig:  # pylint: disable=too-many-instance-attributes
    """Parâmetros de recuperação e seleção de contexto."""

    limit: int
    candidate_limit: int
    max_distance: float | None
    mode: str = "hybrid"
    vector_weight: float = 0.65
    lexical_weight: float = 0.25
    term_overlap_weight: float = 0.10
    neighbor_window: int = 1
    max_per_document: int = 4
    max_per_section: int = 2
    enable_query_decomposition: bool = True
    per_subquery_limit: int = 4
    summary_limit: int = 3


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

        retrieval_question = self._strip_leading_greeting(question)
        subtasks = self._decompose_question(retrieval_question)
        context_limit = self._context_limit(
            requested_limit=search_limit,
            subtasks=subtasks,
        )
        chunks = self._retrieve_context_chunks(
            question=retrieval_question,
            candidate_limit=candidate_limit,
            context_limit=context_limit,
            subtasks=subtasks,
        )
        logger.debug(f"Busca RAG retornou {len(chunks)} chunks.")
        prompt = self._build_prompt(
            question=question,
            chunks=chunks,
            history=history,
            subtasks=subtasks,
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
        subtasks: list[QuerySubtask] | None = None,
    ) -> str:
        """Monta o prompt com instruções, contexto e pergunta."""

        context = self._format_context(chunks)
        formatted_history = self._format_history(history or [])
        formatted_subtasks = self._format_subtasks(subtasks or [])

        return (
            f"{self.config.prompt.system_prompt}\n"
            "Se o contexto responder só parte da pergunta, responda a parte "
            "apoiada nos blocos e diga quais partes não foram encontradas. "
            "Se nenhum bloco útil existir, responda exatamente: "
            f"{self.config.prompt.empty_context_message}\n\n"
            f"Modo de resposta: {self.config.prompt.response_mode}\n\n"
            f"Subtarefas esperadas:\n{formatted_subtasks}\n\n"
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
            metadata = self._format_chunk_metadata(retrieved)
            block = (
                f"[{index}] {metadata}\n"
                f"{retrieved.content}"
            )

            if total_chars + len(block) > self.config.prompt.max_context_chars:
                break

            blocks.append(block)
            total_chars += len(block)

        if not blocks:
            return "Nenhum contexto encontrado."

        return "\n\n".join(blocks)

    def _format_chunk_metadata(self, retrieved: RetrievedChunk) -> str:
        """Formata metadados compactos para o bloco de contexto."""

        parts = [
            f"Documento: {retrieved.document_filename}",
            f"trecho: {retrieved.chunk_index}",
        ]

        if retrieved.page is not None:
            parts.append(f"página: {retrieved.page}")

        if retrieved.section:
            parts.append(f"seção: {retrieved.section}")

        parts.append(f"score: {retrieved.score:.4f}")

        if retrieved.vector_distance is not None:
            parts.append(f"distância vetorial: {retrieved.vector_distance:.4f}")

        if retrieved.lexical_score is not None:
            parts.append(f"score lexical: {retrieved.lexical_score:.4f}")

        if retrieved.subquery:
            parts.append(f"subtarefa: {retrieved.subquery}")

        if retrieved.chunk_type != "content":
            parts.append(f"tipo: {retrieved.chunk_type}")

        return "; ".join(parts)

    def _format_subtasks(self, subtasks: list[QuerySubtask]) -> str:
        """Formata subtarefas para orientar modelos pequenos."""

        if not subtasks:
            return "Responder diretamente à pergunta."

        return "\n".join(
            f"- {subtask.label}: {subtask.query}"
            for subtask in subtasks
        )

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
        """Deduplica, diversifica e limita os chunks enviados ao prompt."""

        selected = []
        seen_hashes = set()
        document_counts: dict[str, int] = {}
        section_counts: dict[tuple[str, str], int] = {}
        unique_documents = {
            chunk.document_filename
            for chunk in chunks
        }
        enforce_document_diversity = len(unique_documents) > 1

        for chunk in chunks:
            content_key = chunk.content_hash

            if content_key in seen_hashes:
                continue

            document_key = chunk.document_filename
            section_key = (document_key, chunk.section or "")

            if (
                enforce_document_diversity
                and
                document_counts.get(document_key, 0)
                >= self.config.retrieval.max_per_document
            ):
                continue

            if (
                chunk.section
                and section_counts.get(section_key, 0)
                >= self.config.retrieval.max_per_section
            ):
                continue

            seen_hashes.add(content_key)
            selected.append(chunk)
            document_counts[document_key] = document_counts.get(document_key, 0) + 1
            section_counts[section_key] = section_counts.get(section_key, 0) + 1

            if len(selected) >= limit:
                break

            for neighbor in self._neighbor_context_chunks(chunk):
                if len(selected) >= limit:
                    break

                if neighbor.content_hash in seen_hashes:
                    continue

                seen_hashes.add(neighbor.content_hash)
                selected.append(neighbor)

        return selected

    def _retrieve_context_chunks(
        self,
        question: str,
        candidate_limit: int,
        context_limit: int,
        subtasks: list[QuerySubtask],
    ) -> list[RetrievedChunk]:
        """Recupera contexto direto ou por subtarefas."""

        if not subtasks:
            question_embedding = self.dependencies.embedding_service.generate(
                question
            )
            chunks = self._retrieve_chunks(
                question=question,
                embedding=question_embedding,
                limit=candidate_limit,
            )
            return self._select_context_chunks(
                chunks=chunks,
                limit=context_limit,
            )

        candidates = []

        if self.config.retrieval.summary_limit > 0:
            summary_embedding = self.dependencies.embedding_service.generate(
                question
            )
            candidates.extend(
                self._tag_retrieved_chunks(
                    chunks=self._retrieve_chunks(
                        question=question,
                        embedding=summary_embedding,
                        limit=self.config.retrieval.summary_limit,
                        chunk_type="summary",
                    ),
                    subquery="resumo",
                )
            )

        for subtask in subtasks:
            subquery_embedding = self.dependencies.embedding_service.generate(
                subtask.query
            )
            subquery_chunks = self._retrieve_chunks(
                question=subtask.query,
                embedding=subquery_embedding,
                limit=self.config.retrieval.per_subquery_limit,
                chunk_type="content",
            )
            candidates.extend(
                self._select_context_chunks(
                    chunks=self._tag_retrieved_chunks(
                        chunks=subquery_chunks,
                        subquery=subtask.label,
                    ),
                    limit=self.config.retrieval.per_subquery_limit,
                )
            )

        return self._select_context_chunks(
            chunks=candidates,
            limit=context_limit,
        )

    def _retrieve_chunks(
        self,
        question: str,
        embedding: list[float],
        limit: int,
        chunk_type: str | None = None,
    ) -> list[RetrievedChunk]:
        """Executa o modo de recuperação configurado."""

        if (
            self.config.retrieval.mode == "hybrid"
            and hasattr(self.dependencies.chunk_repository, "search_hybrid")
        ):
            return self.dependencies.chunk_repository.search_hybrid(
                query=question,
                embedding=embedding,
                options=HybridSearchOptions(
                    limit=limit,
                    vector_limit=limit,
                    lexical_limit=limit,
                    max_distance=self.config.retrieval.max_distance,
                    weights=HybridSearchWeights(
                        vector=self.config.retrieval.vector_weight,
                        lexical=self.config.retrieval.lexical_weight,
                        term_overlap=(
                            self.config.retrieval.term_overlap_weight
                        ),
                    ),
                    chunk_type=chunk_type,
                ),
            )

        if chunk_type is None:
            return self.dependencies.chunk_repository.search_similar(
                embedding=embedding,
                limit=limit,
                max_distance=self.config.retrieval.max_distance,
            )

        try:
            return self.dependencies.chunk_repository.search_similar(
                embedding=embedding,
                limit=limit,
                max_distance=self.config.retrieval.max_distance,
                chunk_type=chunk_type,
            )
        except TypeError:
            return self.dependencies.chunk_repository.search_similar(
                embedding=embedding,
                limit=limit,
                max_distance=self.config.retrieval.max_distance,
            )

    def _tag_retrieved_chunks(
        self,
        chunks: list[RetrievedChunk],
        subquery: str,
    ) -> list[RetrievedChunk]:
        """Marca a subtarefa que trouxe cada chunk."""

        return [
            RetrievedChunk(
                chunk=chunk.chunk,
                score=chunk.score,
                vector_distance=chunk.vector_distance,
                lexical_score=chunk.lexical_score,
                term_overlap=chunk.term_overlap,
                subquery=subquery,
            )
            for chunk in chunks
        ]

    def _neighbor_context_chunks(
        self,
        retrieved: RetrievedChunk,
    ) -> list[RetrievedChunk]:
        """Busca vizinhos do chunk no mesmo documento quando configurado."""

        if self.config.retrieval.neighbor_window <= 0 or not hasattr(
            self.dependencies.chunk_repository,
            "get_neighbors",
        ):
            return []

        document_id = getattr(retrieved.chunk, "document_id", None)

        if document_id is None:
            return []

        neighbors = self.dependencies.chunk_repository.get_neighbors(
            document_id=document_id,
            chunk_index=retrieved.chunk_index,
            window=self.config.retrieval.neighbor_window,
        )

        return [
            RetrievedChunk(
                chunk=chunk,
                score=retrieved.score * 0.95,
                vector_distance=retrieved.vector_distance,
                lexical_score=retrieved.lexical_score,
                term_overlap=retrieved.term_overlap,
                subquery=retrieved.subquery,
            )
            for chunk in neighbors
        ]

    def _decompose_question(self, question: str) -> list[QuerySubtask]:
        """Decompõe perguntas analíticas compostas em buscas focadas."""

        if not self.config.retrieval.enable_query_decomposition:
            return []

        normalized_question = self._normalize_question(question)

        if not self._is_complex_analytical_question(normalized_question):
            return []

        subtasks = []

        if any(
            term in normalized_question
            for term in ("tema", "assunto", "sobre o que")
        ):
            subtasks.append(
                QuerySubtask(
                    label="tema",
                    query="tema objetivo escopo contribuição dissertação",
                )
            )

        if any(
            term in normalized_question
            for term in (
                "pontos fortes",
                "fortes",
                "vantagens",
                "contribuicoes",
            )
        ):
            subtasks.append(
                QuerySubtask(
                    label="pontos fortes",
                    query=(
                        "contribuições vantagens resultados positivos "
                        "pontos fortes"
                    ),
                )
            )

        if any(
            term in normalized_question
            for term in (
                "pontos fracos",
                "fracos",
                "limitacoes",
                "limitações",
            )
        ):
            subtasks.append(
                QuerySubtask(
                    label="pontos fracos",
                    query=(
                        "limitações fraquezas ressalvas dificuldades "
                        "trabalhos futuros"
                    ),
                )
            )

        if any(
            term in normalized_question
            for term in (
                "melhor modelo",
                "modelo testado",
                "melhor algoritmo",
                "modelo",
            )
        ):
            subtasks.append(
                QuerySubtask(
                    label="melhor modelo",
                    query=(
                        "melhor modelo resultados MAE R2 RF LGBM XGBoost "
                        "Prophet Time-LLM Chronos"
                    ),
                )
            )

        if not subtasks:
            subtasks.append(
                QuerySubtask(
                    label="síntese",
                    query=question,
                )
            )

        return subtasks

    def _is_complex_analytical_question(self, normalized_question: str) -> bool:
        """Detecta perguntas que precisam de síntese multi-evidência."""

        complex_markers = {
            "resuma",
            "sintetize",
            "analise",
            "compare",
            "pontos fortes",
            "pontos fracos",
            "melhor modelo",
            "limitacoes",
        }

        return (
            any(marker in normalized_question for marker in complex_markers)
            or normalized_question.count(" e ") >= 2
        )

    def _context_limit(
        self,
        requested_limit: int,
        subtasks: list[QuerySubtask],
    ) -> int:
        """Aumenta o contexto apenas para perguntas compostas."""

        if not subtasks:
            return requested_limit

        return max(
            requested_limit,
            self.config.retrieval.summary_limit + len(subtasks) * 2,
        )

    def _strip_leading_greeting(self, question: str) -> str:
        """Remove saudação inicial que prejudica busca semântica."""

        stripped = re.sub(
            r"^\s*(oi|ol[aá]|bom dia|boa tarde|boa noite)[,!.\s]+",
            "",
            question,
            flags=re.IGNORECASE,
        ).strip()

        return stripped or question

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
