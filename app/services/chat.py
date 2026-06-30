from dataclasses import dataclass

import requests
from requests import HTTPError, RequestException

from app.config.settings import settings
from app.utils import logger


@dataclass(frozen=True)
class ChatServiceConfig:
    """Configuração do chat local."""

    ollama_url: str
    chat_model: str
    timeout_seconds: int
    temperature: float
    top_p: float
    num_ctx: int | None

    @classmethod
    def from_settings(cls) -> "ChatServiceConfig":
        """Cria a configuração padrão a partir das settings da aplicação."""

        return cls(
            ollama_url=settings.OLLAMA_URL,
            chat_model=settings.CHAT_MODEL,
            timeout_seconds=settings.CHAT_TIMEOUT_SECONDS,
            temperature=settings.OLLAMA_TEMPERATURE,
            top_p=settings.OLLAMA_TOP_P,
            num_ctx=settings.OLLAMA_NUM_CTX,
        )


class ChatServiceError(RuntimeError):
    """Erro de comunicação ou resposta inválida do provedor de chat."""


class ChatService:
    """Serviço responsável por gerar respostas usando Ollama local."""

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
    def chat_model(self) -> str:
        """Modelo de chat configurado."""

        return self.config.chat_model

    @property
    def timeout_seconds(self) -> int:
        """Timeout das chamadas HTTP ao provedor."""

        return self.config.timeout_seconds

    @classmethod
    def from_overrides(
        cls,
        chat_model: str | None = None,
    ) -> "ChatService":
        """Cria o serviço aplicando overrides mínimos sobre as settings."""

        default_config = ChatServiceConfig.from_settings()
        return cls(
            ChatServiceConfig(
                ollama_url=default_config.ollama_url,
                chat_model=chat_model or default_config.chat_model,
                timeout_seconds=default_config.timeout_seconds,
                temperature=default_config.temperature,
                top_p=default_config.top_p,
                num_ctx=default_config.num_ctx,
            )
        )

    def generate(self, prompt: str) -> str:
        """Gera uma resposta a partir de um prompt."""

        logger.debug(
            f"Gerando resposta local com Ollama, modelo={self.chat_model}, "
            f"caracteres_prompt={len(prompt)}"
        )
        return self._generate_with_ollama(prompt)

    def _generate_with_ollama(self, prompt: str) -> str:
        """Gera resposta usando o endpoint local do Ollama."""

        options = {
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
        }

        if self.config.num_ctx is not None:
            options["num_ctx"] = self.config.num_ctx

        try:
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
                    "options": options,
                },
                timeout=self.timeout_seconds,
            )
        except RequestException as error:
            raise ChatServiceError(
                "Falha de comunicação com Ollama "
                f"em {self.ollama_url} para o modelo {self.chat_model}: "
                f"{error}"
            ) from error

        self._raise_for_status(response)

        data = response.json()

        answer = data["message"]["content"].strip()
        logger.debug(f"Resposta Ollama recebida com {len(answer)} caracteres.")

        return answer

    def _raise_for_status(self, response: requests.Response) -> None:
        """Levanta erro com contexto do Ollama."""

        try:
            response.raise_for_status()
        except HTTPError as error:
            body = response.text.strip()
            message = (
                f"Ollama retornou erro HTTP {response.status_code} "
                f"para o modelo {self.chat_model}."
            )

            if body:
                message = f"{message} Detalhes: {body}"

            raise ChatServiceError(message) from error
