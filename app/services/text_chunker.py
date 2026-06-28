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
