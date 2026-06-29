from dataclasses import dataclass

from app.config.settings import settings


@dataclass(frozen=True)
class ChatProfile:
    """Configuração de chat de um perfil RAG."""

    provider: str
    model: str


@dataclass(frozen=True)
class RetrievalProfile:
    """Configuração de recuperação de um perfil RAG."""

    limit: int
    candidate_limit: int
    max_context_chars: int


@dataclass(frozen=True)
class RagProfile:
    """Configuração de execução para um perfil do RAG."""

    name: str
    chat: ChatProfile
    embedding_model: str
    retrieval: RetrievalProfile
    history_limit: int
    response_mode: str

    @property
    def chat_provider(self) -> str:
        """Provedor de chat configurado no perfil."""

        return self.chat.provider

    @property
    def chat_model(self) -> str:
        """Modelo de chat configurado no perfil."""

        return self.chat.model

    @property
    def retrieval_limit(self) -> int:
        """Quantidade de chunks enviados ao contexto."""

        return self.retrieval.limit

    @property
    def candidate_limit(self) -> int:
        """Quantidade de candidatos recuperados antes da seleção final."""

        return self.retrieval.candidate_limit

    @property
    def max_context_chars(self) -> int:
        """Limite de caracteres do contexto no prompt."""

        return self.retrieval.max_context_chars


PROFILES = {
    "fast_local": RagProfile(
        name="fast_local",
        chat=ChatProfile(
            provider="ollama",
            model="llama3.2:3b",
        ),
        embedding_model="bge-m3",
        retrieval=RetrievalProfile(
            limit=3,
            candidate_limit=6,
            max_context_chars=3200,
        ),
        history_limit=2,
        response_mode="concise",
    ),
    "balanced_local": RagProfile(
        name="balanced_local",
        chat=ChatProfile(
            provider="ollama",
            model="qwen2.5:7b-instruct",
        ),
        embedding_model="bge-m3",
        retrieval=RetrievalProfile(
            limit=5,
            candidate_limit=8,
            max_context_chars=6000,
        ),
        history_limit=4,
        response_mode="analytical",
    ),
    "deep_local": RagProfile(
        name="deep_local",
        chat=ChatProfile(
            provider="ollama",
            model="llama3.2:3b",
        ),
        embedding_model="bge-m3",
        retrieval=RetrievalProfile(
            limit=5,
            candidate_limit=8,
            max_context_chars=6500,
        ),
        history_limit=4,
        response_mode="deep",
    ),
    "quality_openai": RagProfile(
        name="quality_openai",
        chat=ChatProfile(
            provider="openai",
            model="gpt-4o-mini",
        ),
        embedding_model="bge-m3",
        retrieval=RetrievalProfile(
            limit=8,
            candidate_limit=12,
            max_context_chars=12000,
        ),
        history_limit=6,
        response_mode="analytical",
    ),
}


def get_profile(profile_name: str | None = None) -> RagProfile:
    """Retorna o perfil solicitado ou o perfil padrão configurado."""

    selected_name = profile_name or settings.RAG_PROFILE

    try:
        return PROFILES[selected_name]
    except KeyError as error:
        available_profiles = ", ".join(sorted(PROFILES))
        raise ValueError(
            f"Perfil RAG não suportado: {selected_name}. "
            f"Perfis disponíveis: {available_profiles}."
        ) from error
