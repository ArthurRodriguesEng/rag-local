import hashlib
import re
from dataclasses import dataclass

from app.services.document_loader import DocumentSegment


@dataclass(frozen=True)
class TextChunk:
    """Chunk estruturado pronto para embedding e persistência."""

    content: str
    page: int | None = None
    section: str | None = None
    start_char: int = 0
    end_char: int = 0
    content_hash: str = ""


@dataclass(frozen=True)
class _TextUnit:
    """Unidade textual usada internamente pelo chunker estruturado."""

    content: str
    start_char: int
    end_char: int


class TextChunker:
    """Serviço responsável por dividir textos grandes em chunks."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, text: str) -> list[str]:
        """Divide um texto em chunks com sobreposição."""

        if not text.strip():
            return []

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            start += self.chunk_size - self.chunk_overlap

        return chunks


class StructuredTextChunker:
    """Divide texto preservando página, seção, parágrafos e sentenças."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        chunk_min_size: int = 180,
    ) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap deve ser menor que chunk_size.")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunk_min_size = chunk_min_size

    def split(self, text: str) -> list[str]:
        """Mantém compatibilidade retornando apenas o conteúdo dos chunks."""

        segment = DocumentSegment(
            content=text,
            start_char=0,
            end_char=len(text),
        )
        return [chunk.content for chunk in self.split_segments([segment])]

    def split_segments(
        self,
        segments: list[DocumentSegment],
    ) -> list[TextChunk]:
        """Divide segmentos em chunks com metadados estruturados."""

        chunks = []

        for segment in segments:
            normalized = self.normalize_text(segment.content)

            if not normalized:
                continue

            for section, section_text, section_start in self._section_blocks(
                normalized
            ):
                units = self._split_units(section_text, section_start)
                chunks.extend(
                    self._merge_units(
                        units=units,
                        segment=segment,
                        section=section or segment.section,
                    )
                )

        return chunks

    def normalize_text(self, text: str) -> str:
        """Normaliza quebras, hifenização e espaços excessivos."""

        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n[ \t]+", "\n", text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def _section_blocks(self, text: str) -> list[tuple[str | None, str, int]]:
        """Agrupa texto por seções detectadas por linhas de título."""

        blocks: list[tuple[str | None, str, int]] = []
        current_section = None
        current_lines = []
        current_start = 0
        cursor = 0

        for raw_line in text.splitlines(keepends=True):
            line = raw_line.strip()
            line_start = cursor
            cursor += len(raw_line)

            if self._is_section_heading(line):
                if current_lines:
                    blocks.append(
                        (
                            current_section,
                            "".join(current_lines).strip(),
                            current_start,
                        )
                    )

                current_section = line
                current_lines = [raw_line]
                current_start = line_start
                continue

            if not current_lines and line:
                current_start = line_start

            current_lines.append(raw_line)

        if current_lines:
            block = "".join(current_lines).strip()

            if block:
                blocks.append((current_section, block, current_start))

        return blocks

    def _is_section_heading(self, line: str) -> bool:
        """Detecta títulos curtos comuns em TXT/PDF sem parser semântico."""

        if not line or len(line) > 120:
            return False

        if self._is_table_like_line(line):
            return False

        heading = bool(
            line.startswith("#") or re.match(r"^\d+(\.\d+)*\s+\S", line)
        )

        if not heading and not line.endswith((".", ":", ";", ",")):
            words = line.split()

            if len(words) <= 12:
                letters = [
                    character for character in line if character.isalpha()
                ]
                uppercase_count = sum(
                    character.isupper() for character in letters
                )
                heading = bool(letters) and uppercase_count >= max(
                    3,
                    len(letters) // 2,
                )

        return heading

    def _is_table_like_line(self, line: str) -> bool:
        """Evita tratar cabeçalhos/linhas curtas de tabelas como seções."""

        words = line.split()
        upper_line = line.upper()

        if re.match(r"^\d+(\.\d+)*\s+\S", line):
            return False

        if len(words) == 1 and upper_line in {"RF", "XGB", "LGBM", "R2"}:
            return True

        table_tokens = {"MAE", "RMSE", "REQM", "EAM", "R2", "EXP."}

        if any(token in upper_line for token in table_tokens):
            return True

        return bool(re.search(r"\d", line)) and len(words) <= 8

    def _split_units(self, text: str, base_start: int) -> list[_TextUnit]:
        """Divide um bloco em parágrafos e sentenças sem cortes ruins."""

        units = []
        for match in re.finditer(r"\S(?:.*?\S)?(?:\n\s*\n|$)", text, re.DOTALL):
            paragraph = match.group(0).strip()

            if not paragraph:
                continue

            paragraph_start = base_start + match.start()

            if len(paragraph) <= self.chunk_size:
                units.append(
                    _TextUnit(
                        content=paragraph,
                        start_char=paragraph_start,
                        end_char=paragraph_start + len(paragraph),
                    )
                )
                continue

            units.extend(self._split_sentences(paragraph, paragraph_start))

        if not units and text.strip():
            stripped = text.strip()
            start = base_start + text.find(stripped)
            units.append(
                _TextUnit(
                    content=stripped,
                    start_char=start,
                    end_char=start + len(stripped),
                )
            )

        return units

    def _split_sentences(
        self,
        paragraph: str,
        paragraph_start: int,
    ) -> list[_TextUnit]:
        """Divide parágrafos longos em sentenças."""

        units = []

        for match in re.finditer(r"[^.!?]+(?:[.!?]+|$)", paragraph):
            sentence = match.group(0).strip()

            if not sentence:
                continue

            sentence_start = paragraph_start + match.start()

            if len(sentence) <= self.chunk_size:
                units.append(
                    _TextUnit(
                        content=sentence,
                        start_char=sentence_start,
                        end_char=sentence_start + len(sentence),
                    )
                )
                continue

            units.extend(self._hard_split(sentence, sentence_start))

        return units

    def _hard_split(self, text: str, start_char: int) -> list[_TextUnit]:
        """Último recurso para textos sem separadores naturais."""

        units = []
        start = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            content = text[start:end].strip()

            if content:
                slice_text = text[start:end]
                leading_spaces = len(slice_text) - len(slice_text.lstrip())
                absolute_start = start_char + start + leading_spaces
                units.append(
                    _TextUnit(
                        content=content,
                        start_char=absolute_start,
                        end_char=absolute_start + len(content),
                    )
                )

            start += self.chunk_size

        return units

    def _merge_units(
        self,
        units: list[_TextUnit],
        segment: DocumentSegment,
        section: str | None,
    ) -> list[TextChunk]:
        """Agrupa unidades em chunks respeitando tamanho e overlap."""

        chunks = []
        current: list[_TextUnit] = []

        for unit in units:
            candidate = self._join_units([*current, unit])

            if len(candidate) <= self.chunk_size:
                current.append(unit)
                continue

            if current:
                chunks.append(self._build_chunk(current, segment, section))

            current = [*self._overlap_units(current), unit]

            if len(self._join_units(current)) > self.chunk_size:
                chunks.append(self._build_chunk([unit], segment, section))
                current = []

        if current:
            if (
                chunks
                and len(self._join_units(current)) < self.chunk_min_size
                and len(chunks[-1].content) + len(self._join_units(current))
                <= self.chunk_size
            ):
                previous = _TextUnit(
                    content=chunks[-1].content,
                    start_char=chunks[-1].start_char - segment.start_char,
                    end_char=chunks[-1].end_char - segment.start_char,
                )
                chunks[-1] = self._build_chunk(
                    [previous, *current],
                    segment,
                    section,
                )
            else:
                chunks.append(self._build_chunk(current, segment, section))

        return chunks

    def _overlap_units(self, units: list[_TextUnit]) -> list[_TextUnit]:
        """Retorna unidades finais que cabem no orçamento de overlap."""

        selected = []
        total = 0

        for unit in reversed(units):
            unit_length = len(unit.content)

            if selected and total + unit_length > self.chunk_overlap:
                break

            selected.append(unit)
            total += unit_length

        return list(reversed(selected))

    def _build_chunk(
        self,
        units: list[_TextUnit],
        segment: DocumentSegment,
        section: str | None,
    ) -> TextChunk:
        """Monta um chunk estruturado a partir de unidades."""

        content = self._join_units(units)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        start_char = segment.start_char + min(unit.start_char for unit in units)
        end_char = segment.start_char + max(unit.end_char for unit in units)

        return TextChunk(
            content=content,
            page=segment.page,
            section=section,
            start_char=start_char,
            end_char=end_char,
            content_hash=content_hash,
        )

    def _join_units(self, units: list[_TextUnit]) -> str:
        """Une unidades com separação estável para embeddings."""

        return "\n\n".join(
            unit.content.strip()
            for unit in units
            if unit.content.strip()
        )


class RecursiveTextChunker:
    """Divide textos em chunks tentando preservar a estrutura natural."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap deve ser menor que chunk_size.")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.separators = [
            "\n\n",
            "\n",
            ". ",
            " ",
            "",
        ]

    def split(self, text: str) -> list[str]:
        """Divide o texto em chunks."""

        clean_text = self._normalize_text(text)

        if not clean_text:
            return []

        chunks = self._split_recursive(
            text=clean_text,
            separators=self.separators,
        )

        return self._merge_chunks(chunks)

    def _normalize_text(self, text: str) -> str:
        """Remove espaços excessivos do texto."""

        return text.strip()

    def _split_recursive(
        self,
        text: str,
        separators: list[str],
    ) -> list[str]:
        """Divide o texto usando separadores em ordem de prioridade."""

        if len(text) <= self.chunk_size:
            return [text]

        separator = separators[0]
        remaining_separators = separators[1:]

        if separator == "":
            return [
                text[index : index + self.chunk_size]
                for index in range(0, len(text), self.chunk_size)
            ]

        parts = text.split(separator)

        if len(parts) == 1:
            return self._split_recursive(
                text=text,
                separators=remaining_separators,
            )

        chunks = []

        for part in parts:
            part = part.strip()

            if not part:
                continue

            if len(part) <= self.chunk_size:
                chunks.append(part)
            else:
                chunks.extend(
                    self._split_recursive(
                        text=part,
                        separators=remaining_separators,
                    )
                )

        return chunks

    def _merge_chunks(self, parts: list[str]) -> list[str]:
        """Agrupa partes pequenas em chunks maiores com overlap."""

        chunks = []
        current_chunk = ""

        for part in parts:
            candidate = f"{current_chunk} {part}".strip()

            if len(candidate) <= self.chunk_size:
                current_chunk = candidate
                continue

            if current_chunk:
                chunks.append(current_chunk)

            overlap_text = self._get_overlap(current_chunk)
            current_chunk = f"{overlap_text} {part}".strip()

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _get_overlap(self, text: str) -> str:
        """Retorna o trecho final usado como sobreposição."""

        if not text:
            return ""

        return text[-self.chunk_overlap :]
