from pathlib import Path

import fitz


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
