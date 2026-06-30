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
    description="Rápido e econômico para uso local diário.",
    memory_hint="~8-12 GB RAM unificada recomendada",
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
    response_mode="concise",
)

BALANCED = RagProfile(
    name="balanced",
    description="Equilíbrio entre síntese, português e custo local.",
    memory_hint="~12-16 GB RAM unificada recomendada",
    chat=ChatProfile(
        model="gemma3:12b",
    ),
    embedding_model="bge-m3",
    retrieval=RetrievalProfile(
        limit=7,
        candidate_limit=14,
        max_context_chars=9000,
    ),
    memory_limit=4,
    memory_max_chars=1400,
    response_mode="analytical",
)

REASONING = RagProfile(
    name="reasoning",
    description="Mais forte para raciocínio e análise passo a passo.",
    memory_hint="~12-16 GB RAM unificada recomendada",
    chat=ChatProfile(
        model="deepseek-r1:8b",
    ),
    embedding_model="bge-m3",
    retrieval=RetrievalProfile(
        limit=8,
        candidate_limit=16,
        max_context_chars=10000,
    ),
    memory_limit=5,
    memory_max_chars=1600,
    response_mode="analytical",
)

ROBUST = RagProfile(
    name="robust",
    description="Síntese mais robusta para perguntas longas e compostas.",
    memory_hint="~16-24 GB RAM unificada recomendada",
    chat=ChatProfile(
        model="qwen3:14b",
    ),
    embedding_model="bge-m3",
    retrieval=RetrievalProfile(
        limit=9,
        candidate_limit=18,
        max_context_chars=12000,
    ),
    memory_limit=6,
    memory_max_chars=2000,
    response_mode="deep",
)

MAX = RagProfile(
    name="max",
    description="Maior robustez local, com custo de memória e latência altos.",
    memory_hint="24 GB+ RAM unificada recomendada",
    chat=ChatProfile(
        model="mistral-small3.2:24b",
    ),
    embedding_model="bge-m3",
    retrieval=RetrievalProfile(
        limit=10,
        candidate_limit=24,
        max_context_chars=16000,
    ),
    memory_limit=8,
    memory_max_chars=2600,
    response_mode="deep",
)


PROFILES = {
    "fast": FAST,
    "balanced": BALANCED,
    "reasoning": REASONING,
    "robust": ROBUST,
    "max": MAX,
}


def primary_profiles() -> list[RagProfile]:
    """Retorna os cinco perfis disponíveis em ordem de robustez."""

    return [
        FAST,
        BALANCED,
        REASONING,
        ROBUST,
        MAX,
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
