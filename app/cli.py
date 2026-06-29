import argparse
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, text
from sqlalchemy.exc import DataError

from app.config.database import Base, SessionLocal, engine
from app.config.profiles import PROFILES, get_profile
from app.config.settings import settings
from app.models.chunk import Chunk
from app.models.document import Document
from app.repositories.chunk import ChunkRepository
from app.repositories.document import DocumentRepository
from app.services.chat import ChatServiceError
from app.services.embedding import EmbeddingService
from app.services.ingestion import IngestionService
from app.services.rag import RagService
from app.services.rag_builder import build_rag_config, build_rag_dependencies
from app.services.text_chunker import RecursiveTextChunker
from app.utils import logger


@dataclass(frozen=True)
class ChatOverrides:
    """Sobrescritas opcionais de chat recebidas pela CLI."""

    model: str | None = None


@dataclass(frozen=True)
class RagOverrides:
    """Sobrescritas opcionais do RAG recebidas pela CLI."""

    limit: int | None = None
    embedding_model: str | None = None
    system_prompt: str | None = None
    empty_context_message: str | None = None
    response_mode: str | None = None
    memory_limit: int | None = None
    memory_max_chars: int | None = None


@dataclass(frozen=True)
class ConversationOptions:
    """Opções de persistência e continuidade de conversa."""

    conversation_id: str | None = None
    persist: bool = False


@dataclass(frozen=True)
class AskOptions:
    """Opções agregadas para o caso de uso de pergunta."""

    profile_name: str | None = None
    chat: ChatOverrides = field(default_factory=ChatOverrides)
    rag: RagOverrides = field(default_factory=RagOverrides)
    conversation: ConversationOptions = field(default_factory=ConversationOptions)


@dataclass(frozen=True)
class ChatLoopOptions:
    """Opções agregadas para o chat interativo."""

    profile_name: str | None = None
    limit: int | None = None
    chat: ChatOverrides = field(default_factory=ChatOverrides)
    embedding_model: str | None = None
    response_mode: str | None = None
    memory_limit: int | None = None
    memory_max_chars: int | None = None


def init_db() -> None:
    """Inicializa o banco de dados da aplicação."""

    logger.info("Criando extensão vector, se necessário.")
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    logger.info("Criando tabelas mapeadas pelo SQLAlchemy.")
    Base.metadata.create_all(bind=engine)


def reset_db() -> None:
    """Remove e recria todas as tabelas da aplicação."""

    logger.warning("Removendo tabelas existentes.")
    Base.metadata.drop_all(bind=engine)
    init_db()


def clear_db() -> None:
    """Remove documentos e chunks do banco."""

    session = SessionLocal()

    try:
        logger.warning("Removendo todos os chunks e documentos do banco.")
        session.execute(delete(Chunk))
        session.execute(delete(Document))
        session.commit()
        logger.success("Banco limpo com sucesso.")

    except Exception:
        logger.warning("Erro ao limpar o banco. Executando rollback.")
        session.rollback()
        raise

    finally:
        session.close()


def ingest_document(
    file_path: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    embedding_model: str | None = None,
) -> None:
    """Ingere um documento pelo terminal."""

    session = SessionLocal()

    try:
        logger.info(f"Iniciando ingestão: {file_path}")
        text_chunker = None

        if chunk_size is not None or chunk_overlap is not None:
            text_chunker = RecursiveTextChunker(
                chunk_size=(
                    chunk_size
                    if chunk_size is not None
                    else settings.CHUNK_SIZE
                ),
                chunk_overlap=(
                    chunk_overlap
                    if chunk_overlap is not None
                    else settings.CHUNK_OVERLAP
                ),
            )
            logger.debug(
                "Chunker customizado: "
                f"chunk_size={text_chunker.chunk_size}, "
                f"chunk_overlap={text_chunker.chunk_overlap}"
            )

        embedding_service = None

        if embedding_model is not None:
            embedding_service = EmbeddingService(
                embedding_model=embedding_model,
            )
            logger.debug(f"Modelo de embedding customizado: {embedding_model}")

        service = IngestionService(
            session,
            text_chunker=text_chunker,
            embedding_service=embedding_service,
        )
        chunk_repository = ChunkRepository(session)
        logger.info("Extraindo texto, criando chunks e gerando embeddings.")
        document = service.ingest(file_path)
        chunks = chunk_repository.get_by_document(document.id)

        logger.success("Documento ingerido com sucesso.")
        print(f"ID: {document.id}")
        print(f"Arquivo: {document.filename}")
        print(f"Total de chunks: {len(chunks)}")

    finally:
        logger.debug("Fechando sessão do banco após ingestão.")
        session.close()


def ask_question(
    question: str,
    options: AskOptions | None = None,
) -> str | None:
    """Responde uma pergunta usando os documentos ingeridos."""

    options = options or AskOptions()
    session = SessionLocal()

    try:
        logger.info("Preparando pergunta para o RAG.")
        profile = get_profile(options.profile_name)
        selected_embedding_model = (
            options.rag.embedding_model or profile.embedding_model
        )
        selected_chat_model = options.chat.model or profile.chat_model
        service_config = build_rag_config(
            profile=profile,
            limit=options.rag.limit,
            system_prompt=options.rag.system_prompt,
            empty_context_message=options.rag.empty_context_message,
            response_mode=options.rag.response_mode,
            memory_limit=options.rag.memory_limit,
            memory_max_chars=options.rag.memory_max_chars,
        )

        logger.debug(
            f"Perfil RAG: {profile.name}; chat_model={selected_chat_model}; "
            f"embedding_model={selected_embedding_model}; "
            f"limit={service_config.retrieval.limit}; "
            f"response_mode={service_config.prompt.response_mode}; "
            f"memory_limit={service_config.conversation.memory_limit}; "
            f"memory_max_chars={service_config.conversation.memory_max_chars}"
        )

        service = RagService(
            session,
            dependencies=build_rag_dependencies(
                session=session,
                embedding_model=selected_embedding_model,
                chat_model=selected_chat_model,
            ),
            config=service_config,
        )
        logger.info("Processando pergunta no RAG.")
        try:
            response = service.answer(
                question=question,
                limit=service_config.retrieval.limit,
                conversation_id=(
                    UUID(options.conversation.conversation_id)
                    if options.conversation.conversation_id is not None
                    else None
                ),
                persist_conversation=options.conversation.persist,
            )
        except DataError as error:
            if "different vector dimensions" in str(error):
                logger.warning(
                    "O banco contém embeddings com dimensão diferente da "
                    "configuração atual."
                )
                print(
                    "\nVocê trocou o modelo/dimensão de embedding. "
                    "Recrie as tabelas e ingira os documentos novamente:\n"
                )
                print("python -m app.cli reset-db --yes")
                print("python -m app.cli ingest documents/manual_python.txt")
                return None

            raise
        except ChatServiceError as error:
            session.rollback()
            logger.warning(str(error))

            print("\nVerifique o modelo local no Ollama:\n")
            print("docker exec -it rag-ollama ollama list")
            print(f"docker exec -it rag-ollama ollama pull {selected_chat_model}")
            print("\nSe o prompt estiver grande para o modelo, tente reduzir o contexto:")
            print('python -m app.cli ask "sua pergunta" --limit 3')

            return None

        logger.info("Resposta gerada pelo modelo de chat.")
        print(f"Pergunta: {response.question}")
        print(f"Chunks usados: {len(response.chunks)}")
        if response.conversation_id is not None:
            print(f"Conversa: {response.conversation_id}")
        print("\nResposta:")
        print(response.answer)
        print_sources(response.chunks)

        return str(response.conversation_id) if response.conversation_id else None

    finally:
        logger.debug("Fechando sessão do banco após pergunta.")
        session.close()


def print_sources(chunks) -> None:
    """Imprime as fontes usadas na resposta."""

    if not chunks:
        return

    print("\nFontes:")
    for index, retrieved in enumerate(chunks, start=1):
        print(
            f"- [{index}] {retrieved.document_filename}, "
            f"trecho {retrieved.chunk_index}, distância {retrieved.score:.4f}"
        )


def chat_loop(
    options: ChatLoopOptions | None = None,
) -> None:
    """Inicia uma conversa interativa pelo terminal."""

    options = options or ChatLoopOptions()
    conversation_id = None
    logger.info("Chat iniciado. Digite 'sair' para encerrar.")

    try:
        while True:
            question = input("\nVocê: ").strip()

            if question.lower() in {"sair", "exit", "quit"}:
                logger.info("Chat encerrado.")
                return

            if not question:
                continue

            response_conversation_id = ask_question(
                question=question,
                options=AskOptions(
                    profile_name=options.profile_name,
                    chat=options.chat,
                    rag=RagOverrides(
                        limit=options.limit,
                        embedding_model=options.embedding_model,
                        response_mode=options.response_mode,
                        memory_limit=options.memory_limit,
                        memory_max_chars=options.memory_max_chars,
                    ),
                    conversation=ConversationOptions(
                        conversation_id=conversation_id,
                        persist=True,
                    ),
                ),
            )

            if response_conversation_id is not None:
                conversation_id = response_conversation_id

    except KeyboardInterrupt:
        print()
        logger.info("Chat encerrado.")


def list_documents() -> None:
    """Lista documentos cadastrados."""

    session = SessionLocal()

    try:
        documents = DocumentRepository(session).list_all()

        if not documents:
            print("Nenhum documento cadastrado.")
            return

        for document in documents:
            print(f"{document.id} | {document.filename} | {document.uploaded_at}")

    finally:
        session.close()


def build_parser() -> argparse.ArgumentParser:
    """Cria o parser de argumentos da CLI."""

    parser = argparse.ArgumentParser(
        prog="rag-local",
        description="RAG local no terminal.",
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "init-db",
        help="Cria a extensão vector e as tabelas.",
    )

    reset_parser = subparsers.add_parser(
        "reset-db",
        help="Remove e recria todas as tabelas.",
    )
    reset_parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirma a recriação sem prompt interativo.",
    )

    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Ingere um arquivo .txt ou .pdf.",
    )
    ingest_parser.add_argument(
        "file_path",
        type=str,
        help="Caminho do arquivo que será ingerido.",
    )
    ingest_parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        help="Tamanho máximo de cada chunk.",
    )
    ingest_parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=None,
        help="Sobreposição entre chunks.",
    )
    ingest_parser.add_argument(
        "--embedding-model",
        type=str,
        default=None,
        help="Modelo de embedding usado nesta ingestão.",
    )

    ask_parser = subparsers.add_parser(
        "ask",
        help="Faz uma pergunta usando os documentos ingeridos.",
    )
    ask_parser.add_argument(
        "question",
        nargs="+",
        help="Pergunta enviada ao RAG.",
    )
    ask_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Quantidade máxima de chunks usados como contexto.",
    )
    ask_parser.add_argument(
        "--chat-model",
        type=str,
        default=None,
        help="Modelo local do Ollama usado nesta pergunta.",
    )
    ask_parser.add_argument(
        "--embedding-model",
        type=str,
        default=None,
        help="Modelo de embedding usado nesta pergunta.",
    )
    ask_parser.add_argument(
        "--system-prompt",
        type=str,
        default=None,
        help="Instrução base enviada ao modelo de chat.",
    )
    ask_parser.add_argument(
        "--empty-context-message",
        type=str,
        default=None,
        help="Mensagem usada quando não houver contexto suficiente.",
    )
    ask_parser.add_argument(
        "--profile",
        type=str,
        choices=sorted(PROFILES),
        default=None,
        help="Perfil de execução do RAG.",
    )
    ask_parser.add_argument(
        "--response-mode",
        type=str,
        choices=["concise", "analytical", "deep"],
        default=None,
        help="Nível de profundidade da resposta.",
    )
    ask_parser.add_argument(
        "--memory-limit",
        type=int,
        default=None,
        help="Quantidade de mensagens recentes usadas como memória.",
    )
    ask_parser.add_argument(
        "--memory-max-chars",
        type=int,
        default=None,
        help="Limite de caracteres da memória enviada ao prompt.",
    )
    ask_parser.add_argument(
        "--conversation-id",
        type=str,
        default=None,
        help="ID de uma conversa existente para manter histórico.",
    )
    ask_parser.add_argument(
        "--save-conversation",
        action="store_true",
        help="Salva pergunta e resposta no histórico de conversa.",
    )

    chat_parser = subparsers.add_parser(
        "chat",
        help="Inicia um chat interativo com histórico.",
    )
    chat_parser.add_argument(
        "--profile",
        type=str,
        choices=sorted(PROFILES),
        default=None,
        help="Perfil de execução do RAG.",
    )
    chat_parser.add_argument(
        "--response-mode",
        type=str,
        choices=["concise", "analytical", "deep"],
        default=None,
        help="Nível de profundidade das respostas.",
    )
    chat_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Quantidade máxima de chunks usados como contexto.",
    )
    chat_parser.add_argument(
        "--chat-model",
        type=str,
        default=None,
        help="Modelo local do Ollama usado nesta conversa.",
    )
    chat_parser.add_argument(
        "--embedding-model",
        type=str,
        default=None,
        help="Modelo de embedding usado nesta conversa.",
    )
    chat_parser.add_argument(
        "--memory-limit",
        type=int,
        default=None,
        help="Quantidade de mensagens recentes usadas como memória.",
    )
    chat_parser.add_argument(
        "--memory-max-chars",
        type=int,
        default=None,
        help="Limite de caracteres da memória enviada ao prompt.",
    )

    subparsers.add_parser(
        "documents",
        help="Lista documentos cadastrados.",
    )

    subparsers.add_parser(
        "profiles",
        help="Lista perfis RAG disponíveis.",
    )

    clear_parser = subparsers.add_parser(
        "clear",
        help="Remove todos os documentos e chunks do banco.",
    )
    clear_parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirma a limpeza sem prompt interativo.",
    )

    return parser


def _confirmed(message: str) -> bool:
    """Solicita confirmação simples para comandos destrutivos."""

    confirmation = input(message)
    return confirmation.lower() in {"y", "yes", "s", "sim"}


def _handle_init_db(_args: argparse.Namespace, _parser: argparse.ArgumentParser) -> None:
    """Executa o comando init-db."""

    init_db()
    logger.success("Banco inicializado com sucesso.")


def _handle_reset_db(args: argparse.Namespace, _parser: argparse.ArgumentParser) -> None:
    """Executa o comando reset-db."""

    if not args.yes and not _confirmed(
        "Isso removerá todas as tabelas e dados. Continuar? [y/N] "
    ):
        print("Operação cancelada.")
        return

    reset_db()
    logger.success("Banco recriado com sucesso.")


def _handle_ingest(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Executa o comando ingest."""

    file_path = Path(args.file_path)

    if not file_path.exists():
        parser.error(f"Arquivo não encontrado: {args.file_path}")

    ingest_document(
        file_path=args.file_path,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        embedding_model=args.embedding_model,
    )


def _handle_ask(args: argparse.Namespace, _parser: argparse.ArgumentParser) -> None:
    """Executa o comando ask."""

    ask_question(
        question=" ".join(args.question),
        options=AskOptions(
            profile_name=args.profile,
            chat=ChatOverrides(
                model=args.chat_model,
            ),
            rag=RagOverrides(
                limit=args.limit,
                embedding_model=args.embedding_model,
                system_prompt=args.system_prompt,
                empty_context_message=args.empty_context_message,
                response_mode=args.response_mode,
                memory_limit=args.memory_limit,
                memory_max_chars=args.memory_max_chars,
            ),
            conversation=ConversationOptions(
                conversation_id=args.conversation_id,
                persist=args.save_conversation,
            ),
        ),
    )


def _handle_chat(args: argparse.Namespace, _parser: argparse.ArgumentParser) -> None:
    """Executa o comando chat."""

    chat_loop(
        options=ChatLoopOptions(
            profile_name=args.profile,
            limit=args.limit,
            chat=ChatOverrides(
                model=args.chat_model,
            ),
            embedding_model=args.embedding_model,
            response_mode=args.response_mode,
            memory_limit=args.memory_limit,
            memory_max_chars=args.memory_max_chars,
        ),
    )


def _handle_documents(
    _args: argparse.Namespace,
    _parser: argparse.ArgumentParser,
) -> None:
    """Executa o comando documents."""

    list_documents()


def _handle_profiles(
    _args: argparse.Namespace,
    _parser: argparse.ArgumentParser,
) -> None:
    """Executa o comando profiles."""

    for profile in PROFILES.values():
        print(
            f"{profile.name} | chat={profile.chat_model} | "
            f"embedding={profile.embedding_model} | "
            f"limit={profile.retrieval_limit} | "
            f"contexto={profile.max_context_chars} | "
            f"memoria={profile.memory_limit}/{profile.memory_max_chars} | "
            f"modo={profile.response_mode}"
        )


def _handle_clear(args: argparse.Namespace, _parser: argparse.ArgumentParser) -> None:
    """Executa o comando clear."""

    if not args.yes and not _confirmed(
        "Isso removerá todos os documentos e chunks. Continuar? [y/N] "
    ):
        print("Operação cancelada.")
        return

    clear_db()


COMMAND_HANDLERS = {
    "init-db": _handle_init_db,
    "reset-db": _handle_reset_db,
    "ingest": _handle_ingest,
    "ask": _handle_ask,
    "chat": _handle_chat,
    "documents": _handle_documents,
    "profiles": _handle_profiles,
    "clear": _handle_clear,
}


def main() -> None:
    """Ponto de entrada da CLI."""

    parser = build_parser()
    args = parser.parse_args()
    COMMAND_HANDLERS[args.command](args, parser)


if __name__ == "__main__":
    main()
