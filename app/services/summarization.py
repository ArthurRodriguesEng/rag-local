import re
from dataclasses import dataclass

from app.config.settings import settings
from app.services.chat import ChatService, ChatServiceError
from app.services.text_chunker import TextChunk
from app.utils import logger


@dataclass(frozen=True)
class SummaryChunk:
    """Resumo local persistido como chunk recuperável."""

    content: str
    section: str | None
    page: int | None
    start_char: int | None
    end_char: int | None
    chunk_type: str = "summary"


class SummaryService:
    """Gera resumos locais de seções para perguntas amplas."""

    def __init__(
        self,
        chat_service: ChatService | None = None,
        max_input_chars: int = 4000,
        min_group_chars: int = 900,
        max_summary_chars: int = 1400,
    ) -> None:
        self.chat_service = chat_service or ChatService.from_overrides(
            chat_model=settings.RAG_SUMMARY_MODEL,
        )
        self.max_input_chars = max_input_chars
        self.min_group_chars = min_group_chars
        self.max_summary_chars = max_summary_chars
        self._llm_disabled = False

    def summarize(
        self,
        chunks: list[TextChunk],
        document_name: str,
    ) -> list[SummaryChunk]:
        """Cria resumos por seção e um resumo geral quando possível."""

        groups = self._group_chunks(chunks)
        summaries = []

        for section, section_chunks in groups:
            text = self._join_chunk_text(section_chunks)

            if len(text) < self.min_group_chars:
                continue

            summary = self._summarize_text(
                document_name=document_name,
                section=section,
                text=text,
            )

            if not summary:
                continue

            summaries.append(
                SummaryChunk(
                    content=summary,
                    section=section or "Resumo do documento",
                    page=section_chunks[0].page,
                    start_char=min(chunk.start_char for chunk in section_chunks),
                    end_char=max(chunk.end_char for chunk in section_chunks),
                )
            )

        return summaries

    def _group_chunks(
        self,
        chunks: list[TextChunk],
    ) -> list[tuple[str | None, list[TextChunk]]]:
        """Agrupa chunks por seção preservando a ordem do documento."""

        groups: list[tuple[str | None, list[TextChunk]]] = []
        current_section = None
        current_chunks: list[TextChunk] = []

        for chunk in chunks:
            section = chunk.section or "Sem seção"

            if current_chunks and section != current_section:
                groups.append((current_section, current_chunks))
                current_chunks = []

            current_section = section
            current_chunks.append(chunk)

        if current_chunks:
            groups.append((current_section, current_chunks))

        if chunks:
            groups.insert(0, ("Resumo geral", chunks))

        return groups

    def _join_chunk_text(self, chunks: list[TextChunk]) -> str:
        """Concatena conteúdo com limite para caber no modelo local."""

        text = "\n\n".join(chunk.content for chunk in chunks)
        return text[: self.max_input_chars]

    def _summarize_text(
        self,
        document_name: str,
        section: str | None,
        text: str,
    ) -> str | None:
        """Gera resumo curto com fallback extrativo local."""

        if self._llm_disabled:
            return self._extractive_summary(
                document_name=document_name,
                section=section,
                text=text,
            )

        prompt = (
            "Resuma o trecho abaixo para busca RAG local.\n"
            "Use português do Brasil. Não invente informações.\n"
            "Inclua, quando estiver no trecho: tema, objetivo, método, "
            "resultados, pontos fortes, limitações e melhor modelo.\n\n"
            f"Documento: {document_name}\n"
            f"Seção: {section or 'Sem seção'}\n\n"
            f"Trecho:\n{text}\n\n"
            "Resumo:"
        )

        try:
            return self.chat_service.generate(prompt)
        except ChatServiceError as error:
            self._llm_disabled = True
            logger.warning(
                "Resumo via Ollama falhou; usando resumo extrativo local. "
                "As próximas seções desta ingestão usarão resumo extrativo "
                "direto para evitar reiniciar o modelo repetidamente. "
                f"Detalhes: {error}"
            )
            return self._extractive_summary(
                document_name=document_name,
                section=section,
                text=text,
            )

    def _extractive_summary(
        self,
        document_name: str,
        section: str | None,
        text: str,
    ) -> str:
        """Seleciona frases importantes sem chamar LLM."""

        sentences = self._split_sentences(text)

        if not sentences:
            return ""

        selected = self._rank_sentences(sentences)
        body = " ".join(selected)

        if len(body) > self.max_summary_chars:
            body = body[: self.max_summary_chars].rsplit(" ", 1)[0].strip()

        return (
            "Resumo extrativo para busca RAG. "
            f"Documento: {document_name}. "
            f"Seção: {section or 'Sem seção'}. "
            f"{body}"
        )

    def _split_sentences(self, text: str) -> list[str]:
        """Divide texto em frases úteis para resumo extrativo."""

        normalized = re.sub(r"\s+", " ", text).strip()

        return [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", normalized)
            if len(sentence.strip()) > 40
        ]

    def _rank_sentences(self, sentences: list[str]) -> list[str]:
        """Ordena frases por relevância para perguntas analíticas."""

        scored_sentences = [
            (self._sentence_score(sentence, index), index, sentence)
            for index, sentence in enumerate(sentences)
        ]
        ranked = sorted(
            scored_sentences,
            key=lambda item: (-item[0], item[1]),
        )
        selected_indexes = {
            0,
            *(
                index
                for _score, index, _sentence in ranked[:8]
            ),
        }

        return [
            sentence
            for index, sentence in enumerate(sentences)
            if index in selected_indexes
        ]

    def _sentence_score(self, sentence: str, index: int) -> int:
        """Pontua frases com termos importantes para síntese RAG."""

        normalized = sentence.lower()
        keywords = {
            "objetivo": 4,
            "tema": 4,
            "contribui": 4,
            "resultado": 4,
            "limitação": 5,
            "limitações": 5,
            "trabalhos futuros": 5,
            "melhor modelo": 5,
            "random forest": 4,
            "lightgbm": 4,
            "lgbm": 4,
            "xgboost": 3,
            "prophet": 3,
            "chronos": 3,
            "time-llm": 3,
            "mae": 3,
            "r2": 3,
            "superam": 4,
            "ensemble": 4,
            "fotovoltaica": 3,
            "twin-plant": 3,
        }
        score = sum(
            weight
            for keyword, weight in keywords.items()
            if keyword in normalized
        )

        if index == 0:
            score += 2

        return score
