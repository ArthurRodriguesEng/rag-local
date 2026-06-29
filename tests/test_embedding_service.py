from types import SimpleNamespace

import pytest
import requests

from app.services.embedding import EmbeddingService


def make_response(status_code: int, payload: dict):
    """Cria uma resposta fake compatível com requests.Response."""

    def raise_for_status() -> None:
        if status_code >= 400:
            raise requests.HTTPError(
                f"{status_code} error",
                response=SimpleNamespace(status_code=status_code),
            )

    return SimpleNamespace(
        status_code=status_code,
        json=lambda: payload,
        raise_for_status=raise_for_status,
    )


def test_generate_uses_embed_endpoint_when_available(monkeypatch) -> None:
    calls = []

    def fake_post(url: str, json: dict, timeout: int):
        calls.append((url, json, timeout))
        return make_response(200, {"embeddings": [[0.1, 0.2, 0.3]]})

    monkeypatch.setattr("app.services.embedding.requests.post", fake_post)
    service = EmbeddingService(expected_dimension=3, timeout_seconds=7)

    embedding = service.generate("texto")

    assert embedding == [0.1, 0.2, 0.3]
    assert calls == [
        (
            f"{service.ollama_url}/api/embed",
            {"model": service.embedding_model, "input": "texto"},
            7,
        )
    ]


def test_generate_falls_back_to_legacy_embeddings_endpoint(monkeypatch) -> None:
    calls = []

    def fake_post(url: str, json: dict, timeout: int):
        calls.append((url, json, timeout))
        if url.endswith("/api/embed"):
            return make_response(404, {})
        return make_response(200, {"embedding": [0.4, 0.5, 0.6]})

    monkeypatch.setattr("app.services.embedding.requests.post", fake_post)
    service = EmbeddingService(expected_dimension=3, timeout_seconds=9)

    embedding = service.generate("conteudo")

    assert embedding == [0.4, 0.5, 0.6]
    assert calls == [
        (
            f"{service.ollama_url}/api/embed",
            {"model": service.embedding_model, "input": "conteudo"},
            9,
        ),
        (
            f"{service.ollama_url}/api/embeddings",
            {"model": service.embedding_model, "prompt": "conteudo"},
            9,
        ),
    ]


def test_generate_rejects_unknown_response_format(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.embedding.requests.post",
        lambda url, json, timeout: make_response(200, {"foo": "bar"}),
    )
    service = EmbeddingService(expected_dimension=3)

    with pytest.raises(ValueError, match="formato desconhecido"):
        service.generate("texto")
