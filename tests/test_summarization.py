from app.services.chat import ChatServiceError
from app.services.summarization import SummaryService
from app.services.text_chunker import TextChunk


class FailingChatService:
    """Chat falso que simula processo do Ollama morto."""

    def generate(self, prompt: str) -> str:
        raise ChatServiceError("llama-server process has terminated")


def test_summary_service_falls_back_to_extractive_summary() -> None:
    service = SummaryService(
        chat_service=FailingChatService(),
        min_group_chars=100,
        max_input_chars=2000,
    )
    chunks = [
        TextChunk(
            content=(
                "Esta dissertação estuda previsão de geração fotovoltaica "
                "em configuração Twin-Plant. "
                "Os resultados indicam que modelos de ensemble superam "
                "modelos baseados em LLM. "
                "As limitações incluem ausência de variáveis do rastreador "
                "e dependência de dados meteorológicos."
            ),
            section="Conclusão",
            page=70,
            start_char=0,
            end_char=260,
            content_hash="abc",
        )
    ]

    summaries = service.summarize(
        chunks=chunks,
        document_name="dissertacao.pdf",
    )

    assert summaries
    assert summaries[0].chunk_type == "summary"
    assert "Resumo extrativo" in summaries[0].content
    assert "fotovoltaica" in summaries[0].content
    assert "limitações" in summaries[0].content
