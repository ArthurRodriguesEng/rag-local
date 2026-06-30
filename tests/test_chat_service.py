from requests import HTTPError, ReadTimeout

from app.services.chat import ChatService, ChatServiceConfig, ChatServiceError


class FakeResponse:
    """Resposta HTTP falsa para isolar o provedor de chat."""

    def __init__(
        self,
        payload: dict,
        status_code: int = 200,
        text: str = "",
        should_fail: bool = False,
    ) -> None:
        self.payload = payload
        self.status_code = status_code
        self.text = text
        self.should_fail = should_fail

    def raise_for_status(self) -> None:
        if self.should_fail:
            raise HTTPError("HTTP error", response=self)

    def json(self) -> dict:
        return self.payload


def test_generate_calls_ollama_chat(monkeypatch) -> None:
    calls = []

    def fake_post(url, json, timeout):
        calls.append(
            {
                "url": url,
                "json": json,
                "timeout": timeout,
            }
        )
        return FakeResponse(
            {
                "message": {
                    "content": " resposta final ",
                }
            }
        )

    monkeypatch.setattr("app.services.chat.requests.post", fake_post)

    service = ChatService(ChatServiceConfig.from_settings())
    answer = service.generate("Meu prompt")

    assert answer == "resposta final"
    assert calls[0]["url"].endswith("/api/chat")
    assert calls[0]["json"]["model"] == service.chat_model
    assert calls[0]["json"]["messages"][0]["content"] == "Meu prompt"
    assert calls[0]["json"]["stream"] is False
    assert calls[0]["json"]["options"]["temperature"] == 0.0
    assert calls[0]["json"]["options"]["top_p"] == 0.3
    assert calls[0]["timeout"] == service.timeout_seconds


def test_ollama_http_error_includes_response_body(monkeypatch) -> None:
    def fake_post(url, json, timeout):
        calls = {
            "url": url,
            "json": json,
            "timeout": timeout,
        }
        assert calls["url"].endswith("/api/chat")
        return FakeResponse(
            payload={},
            status_code=500,
            text="model failed to load",
            should_fail=True,
        )

    monkeypatch.setattr("app.services.chat.requests.post", fake_post)

    service = ChatService.from_overrides(
        chat_model="qwen3:4b",
    )

    try:
        service.generate("Meu prompt")
    except ChatServiceError as error:
        assert "Ollama retornou erro HTTP 500" in str(error)
        assert "model failed to load" in str(error)
        assert "qwen3:4b" in str(error)
    else:
        raise AssertionError("Expected ChatServiceError")


def test_ollama_timeout_is_wrapped_as_chat_service_error(monkeypatch) -> None:
    def fake_post(url, json, timeout):
        raise ReadTimeout(
            f"HTTPConnectionPool(host='localhost', port=11434): "
            f"Read timed out. (read timeout={timeout})"
        )

    monkeypatch.setattr("app.services.chat.requests.post", fake_post)

    service = ChatService.from_overrides(
        chat_model="qwen3:8b",
    )

    try:
        service.generate("Meu prompt")
    except ChatServiceError as error:
        assert "Falha de comunicação com Ollama" in str(error)
        assert "qwen3:8b" in str(error)
        assert "Read timed out" in str(error)
    else:
        raise AssertionError("Expected ChatServiceError")
