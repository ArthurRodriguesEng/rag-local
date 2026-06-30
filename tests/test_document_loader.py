from app.services.document_loader import DocumentLoader


def test_load_segments_for_txt_preserves_offsets(tmp_path) -> None:
    file_path = tmp_path / "manual.txt"
    file_path.write_text("Título\n\nConteúdo do documento.", encoding="utf-8")

    segments = DocumentLoader().load_segments(str(file_path))

    assert len(segments) == 1
    assert segments[0].content == "Título\n\nConteúdo do documento."
    assert segments[0].page is None
    assert segments[0].start_char == 0
    assert segments[0].end_char == len(segments[0].content)


def test_load_segments_for_markdown_preserves_text(tmp_path) -> None:
    file_path = tmp_path / "manual.md"
    file_path.write_text("# Título\n\nConteúdo em Markdown.", encoding="utf-8")

    segments = DocumentLoader().load_segments(str(file_path))

    assert len(segments) == 1
    assert segments[0].content == "# Título\n\nConteúdo em Markdown."
    assert segments[0].start_char == 0
    assert segments[0].end_char == len(segments[0].content)
