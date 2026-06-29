import requests

from app.config.settings import settings
from app.utils import logger


class EmbeddingService:
    """Serviço responsável por gerar embeddings usando o Ollama."""

    def __init__(
        self,
        ollama_url: str | None = None,
        embedding_model: str | None = None,
        expected_dimension: int | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.ollama_url = (ollama_url or settings.OLLAMA_URL).rstrip("/")
        self.embedding_model = embedding_model or settings.EMBEDDING_MODEL
        self.expected_dimension = (
            expected_dimension
            if expected_dimension is not None
            else settings.EMBEDDING_DIMENSION
        )
        self.timeout_seconds = (
            timeout_seconds or settings.EMBEDDING_TIMEOUT_SECONDS
        )

    def generate(self, text: str) -> list[float]:
        """Gera embedding para um texto."""

        logger.debug(
            f"Gerando embedding com modelo {self.embedding_model}; "
            f"caracteres={len(text)}"
        )
        response = requests.post(
            f"{self.ollama_url}/api/embed",
            json={
                "model": self.embedding_model,
                "input": text,
            },
            timeout=self.timeout_seconds,
        )

        response.raise_for_status()

        data = response.json()
        embedding = data["embeddings"][0]

        if len(embedding) != self.expected_dimension:
            raise ValueError(
                f"Embedding gerado com dimensão inválida. "
                f"Esperado: {self.expected_dimension}, "
                f"recebido: {len(embedding)}."
            )

        logger.debug(f"Embedding gerado com {len(embedding)} dimensões.")
        return embedding
