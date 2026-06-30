from dataclasses import dataclass

from app.config.settings import settings


@dataclass(frozen=True)
class ChatProfile:
    """Configuração de chat de um perfil RAG."""

    model: str


@dataclass(frozen=True)
class RetrievalProfile:
    """Configuração de recuperação de um perfil RAG."""

    limit: int
    candidate_limit: int
    max_context_chars: int


@dataclass(frozen=True)
class RagProfile:  # pylint: disable=too-many-instance-attributes
    """Configuração de execução para um perfil do RAG."""

    name: str
    description: str
    memory_hint: str
    chat: ChatProfile
    embedding_model: str
    retrieval: RetrievalProfile
    memory_limit: int
    memory_max_chars: int
    response_mode: str

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


FAST = RagProfile(
    name="fast",
    description="Mais rápido e leve para validação e uso local diário.",
    memory_hint="~4-8 GB RAM recomendada",
    chat=ChatProfile(
        model="llama3.2:3b",
    ),
    embedding_model="bge-m3",
    retrieval=RetrievalProfile(
        limit=3,
        candidate_limit=6,
        max_context_chars=3200,
    ),
    memory_limit=2,
    memory_max_chars=700,
    response_mode="concise",
)

BALANCED = RagProfile(
    name="balanced",
    description="Equilíbrio entre qualidade em português e custo local.",
    memory_hint="~8-12 GB RAM recomendada",
    chat=ChatProfile(
        model="qwen3:8b",
    ),
    embedding_model="bge-m3",
    retrieval=RetrievalProfile(
        limit=5,
        candidate_limit=10,
        max_context_chars=6500,
    ),
    memory_limit=3,
    memory_max_chars=1000,
    response_mode="analytical",
)

REASONING = RagProfile(
    name="reasoning",
    description="Mais forte para raciocínio, com maior latência em CPU.",
    memory_hint="~8-12 GB RAM recomendada; use timeout maior em CPU",
    chat=ChatProfile(
        model="deepseek-r1:8b",
    ),
    embedding_model="bge-m3",
    retrieval=RetrievalProfile(
        limit=3,
        candidate_limit=10,
        max_context_chars=14000,
    ),
    memory_limit=5,
    memory_max_chars=2000,
    response_mode="analytical",
)


PROFILES = {
    "fast": FAST,
    "balanced": BALANCED,
    "reasoning": REASONING,
}


def primary_profiles() -> list[RagProfile]:
    """Retorna os perfis disponíveis em ordem de robustez."""

    return [
        FAST,
        BALANCED,
        REASONING,
    ]


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
