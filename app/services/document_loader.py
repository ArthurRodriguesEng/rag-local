from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass(frozen=True)
class DocumentSegment:
    """Trecho de documento com metadados de origem."""

    content: str
    page: int | None = None
    section: str | None = None
    start_char: int = 0
    end_char: int = 0


class DocumentLoader:
    """Serviço responsável por extrair texto de documentos."""

    def load(self, file_path: str) -> str:
        """Carrega um documento e retorna seu texto."""

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        if path.suffix.lower() == ".txt":
            return self._load_txt(path)

        if path.suffix.lower() == ".pdf":
            return self._load_pdf(path)

        raise ValueError(f"Formato de arquivo não suportado: {path.suffix}")

    def load_segments(self, file_path: str) -> list[DocumentSegment]:
        """Carrega um documento preservando páginas e offsets básicos."""

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        if path.suffix.lower() == ".txt":
            return self._load_txt_segments(path)

        if path.suffix.lower() == ".pdf":
            return self._load_pdf_segments(path)

        raise ValueError(f"Formato de arquivo não suportado: {path.suffix}")

    def _load_txt(self, path: Path) -> str:
        """Extrai texto de arquivo TXT."""

        return path.read_text(encoding="utf-8")

    def _load_pdf(self, path: Path) -> str:
        """Extrai texto de arquivo PDF."""

        text_parts = []

        with fitz.open(path) as document:
            for page in document:
                text = page.get_text()

                if text.strip():
                    text_parts.append(text)

        return "\n\n".join(text_parts)

    def _load_txt_segments(self, path: Path) -> list[DocumentSegment]:
        """Extrai texto de TXT como segmento único."""

        text = self._load_txt(path)

        if not text.strip():
            return []

        return [
            DocumentSegment(
                content=text,
                start_char=0,
                end_char=len(text),
            )
        ]

    def _load_pdf_segments(self, path: Path) -> list[DocumentSegment]:
        """Extrai texto de PDF preservando uma unidade por página."""

        segments = []
        absolute_offset = 0

        with fitz.open(path) as document:
            for page_index, page in enumerate(document, start=1):
                text = page.get_text()
                page_start = absolute_offset
                page_end = page_start + len(text)
                absolute_offset = page_end + 2

                if not text.strip():
                    continue

                segments.append(
                    DocumentSegment(
                        content=text,
                        page=page_index,
                        start_char=page_start,
                        end_char=page_end,
                    )
                )

        return segments
