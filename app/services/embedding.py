import requests

from app.config.settings import settings


class EmbeddingService:
    """Serviço responsável por gerar embeddings usando o Ollama."""

    EXPECTED_DIMENSION = 768

    def __init__(self) -> None:
        self.ollama_url = settings.OLLAMA_URL.rstrip("/")
        self.embedding_model = settings.EMBEDDING_MODEL

    def generate(self, text: str) -> list[float]:
        """Gera embedding para um texto."""

        response = requests.post(
            f"{self.ollama_url}/api/embed",
            json={
                "model": self.embedding_model,
                "input": text,
            },
            timeout=60,
        )

        response.raise_for_status()

        data = response.json()
        embedding = data["embeddings"][0]

        if len(embedding) != self.EXPECTED_DIMENSION:
            raise ValueError(
                f"Embedding gerado com dimensão inválida. "
                f"Esperado: {self.EXPECTED_DIMENSION}, "
                f"recebido: {len(embedding)}."
            )

        return embedding
