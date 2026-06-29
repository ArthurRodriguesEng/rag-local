from dataclasses import dataclass

import requests
from requests import HTTPError

from app.config.settings import settings
from app.utils import logger


@dataclass(frozen=True)
class ChatServiceConfig:
    """Configuração do provedor de chat."""

    ollama_url: str
    provider: str
    chat_model: str
    timeout_seconds: int
    openai_api_key: str | None
    openai_base_url: str

    @classmethod
    def from_settings(cls) -> "ChatServiceConfig":
        """Cria a configuração padrão a partir das settings da aplicação."""

        return cls(
            ollama_url=settings.OLLAMA_URL,
            provider=settings.CHAT_PROVIDER,
            chat_model=settings.CHAT_MODEL,
            timeout_seconds=settings.CHAT_TIMEOUT_SECONDS,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_base_url=settings.OPENAI_BASE_URL,
        )


class ChatServiceError(RuntimeError):
    """Erro de comunicação ou resposta inválida do provedor de chat."""


class ChatService:
    """Serviço responsável por gerar respostas usando um provedor de chat."""

    def __init__(
        self,
        config: ChatServiceConfig | None = None,
    ) -> None:
        self.config = config or ChatServiceConfig.from_settings()

    @property
    def ollama_url(self) -> str:
        """URL base normalizada do Ollama."""

        return self.config.ollama_url.rstrip("/")

    @property
    def provider(self) -> str:
        """Nome normalizado do provedor de chat."""

        return self.config.provider.lower()

    @property
    def chat_model(self) -> str:
        """Modelo de chat configurado."""

        return self.config.chat_model

    @property
    def timeout_seconds(self) -> int:
        """Timeout das chamadas HTTP ao provedor."""

        return self.config.timeout_seconds

    @property
    def openai_api_key(self) -> str | None:
        """Chave da OpenAI configurada para o provedor."""

        return self.config.openai_api_key

    @property
    def openai_base_url(self) -> str:
        """URL base normalizada da API compatível com OpenAI."""

        return self.config.openai_base_url.rstrip("/")

    @classmethod
    def from_overrides(
        cls,
        provider: str | None = None,
        chat_model: str | None = None,
        openai_api_key: str | None = None,
    ) -> "ChatService":
        """Cria o serviço aplicando overrides mínimos sobre as settings."""

        default_config = ChatServiceConfig.from_settings()
        return cls(
            ChatServiceConfig(
                ollama_url=default_config.ollama_url,
                provider=provider or default_config.provider,
                chat_model=chat_model or default_config.chat_model,
                timeout_seconds=default_config.timeout_seconds,
                openai_api_key=(
                    openai_api_key
                    if openai_api_key is not None
                    else default_config.openai_api_key
                ),
                openai_base_url=default_config.openai_base_url,
            )
        )

    def generate(self, prompt: str) -> str:
        """Gera uma resposta a partir de um prompt."""

        logger.debug(
            f"Gerando resposta com provider={self.provider}, "
            f"modelo={self.chat_model}, caracteres_prompt={len(prompt)}"
        )
        if self.provider == "ollama":
            return self._generate_with_ollama(prompt)

        if self.provider == "openai":
            return self._generate_with_openai(prompt)

        raise ValueError(f"Provedor de chat não suportado: {self.provider}")

    def _generate_with_ollama(self, prompt: str) -> str:
        """Gera resposta usando o endpoint local do Ollama."""

        response = requests.post(
            f"{self.ollama_url}/api/chat",
            json={
                "model": self.chat_model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                "stream": False,
            },
            timeout=self.timeout_seconds,
        )

        self._raise_for_status(response)

        data = response.json()

        answer = data["message"]["content"].strip()
        logger.debug(f"Resposta Ollama recebida com {len(answer)} caracteres.")

        return answer

    def _generate_with_openai(self, prompt: str) -> str:
        """Gera resposta usando a API da OpenAI."""

        if not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY precisa estar configurada para usar OpenAI."
            )

        response = requests.post(
            f"{self.openai_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.chat_model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            },
            timeout=self.timeout_seconds,
        )

        self._raise_for_status(response)

        data = response.json()

        answer = data["choices"][0]["message"]["content"].strip()
        logger.debug(f"Resposta OpenAI recebida com {len(answer)} caracteres.")

        return answer

    def _raise_for_status(self, response: requests.Response) -> None:
        """Levanta erro com contexto do provedor."""

        try:
            response.raise_for_status()
        except HTTPError as error:
            body = response.text.strip()
            provider = "Ollama" if self.provider == "ollama" else "OpenAI"
            message = (
                f"{provider} retornou erro HTTP {response.status_code} "
                f"para o modelo {self.chat_model}."
            )

            if body:
                message = f"{message} Detalhes: {body}"

            raise ChatServiceError(message) from error
