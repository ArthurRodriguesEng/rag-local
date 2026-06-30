from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centraliza e valida todas as configurações da aplicação."""

    # Execução
    DEBUG: bool = False
    UPLOAD_DIR: str = "uploads"

    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "rag"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    # Ollama
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_TEMPERATURE: float = 0.0
    OLLAMA_TOP_P: float = 0.3
    OLLAMA_NUM_CTX: int | None = None

    # Modelos
    RAG_PROFILE: str = "fast"
    CHAT_MODEL: str = "llama3.2:3b"
    EMBEDDING_MODEL: str = "bge-m3"
    EMBEDDING_DIMENSION: int = 1024
    RAG_SUMMARY_MODEL: str = "llama3.2:3b"

    # Chunking
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    CHUNK_MIN_SIZE: int = 180

    # Recuperação e prompt
    RAG_ENABLE_QUERY_DECOMPOSITION: bool = True
    RAG_ENABLE_SECTION_SUMMARIES: bool = True
    RETRIEVAL_MODE: str = "hybrid"
    RETRIEVAL_LIMIT: int = 5
    RETRIEVAL_CANDIDATE_LIMIT: int = 12
    RETRIEVAL_PER_SUBQUERY_LIMIT: int = 4
    RETRIEVAL_SUMMARY_LIMIT: int = 3
    RETRIEVAL_MAX_DISTANCE: float | None = None
    RETRIEVAL_VECTOR_WEIGHT: float = 0.65
    RETRIEVAL_LEXICAL_WEIGHT: float = 0.25
    RETRIEVAL_TERM_OVERLAP_WEIGHT: float = 0.10
    RETRIEVAL_NEIGHBOR_WINDOW: int = 1
    RETRIEVAL_MAX_PER_DOCUMENT: int = 4
    RETRIEVAL_MAX_PER_SECTION: int = 2
    RAG_MAX_CONTEXT_CHARS: int = 12000
    RAG_MEMORY_LIMIT: int = 6
    RAG_MEMORY_MAX_CHARS: int = 1200
    RAG_RESPONSE_MODE: str = "analytical"
    RAG_PROMPT_PATH: str = "prompts/internal_assistant.md"
    RAG_SYSTEM_PROMPT: str = (
        "Você é um assistente de conhecimento local. "
        "Responda somente com base no contexto fornecido."
    )
    RAG_EMPTY_CONTEXT_MESSAGE: str = (
        "Não encontrei informação suficiente nos documentos."
    )

    # Timeouts
    EMBEDDING_TIMEOUT_SECONDS: int = 60
    CHAT_TIMEOUT_SECONDS: int = 240

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @cached_property
    def database_url(self) -> str:
        """Retorna a URL de conexão utilizada pelo SQLAlchemy."""
        return (
            f"postgresql+psycopg://"
            f"{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )


settings = Settings()
