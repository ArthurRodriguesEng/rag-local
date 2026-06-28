from app.services.text_chunker import TextChunker


def main() -> None:
    text = """
    Python é uma linguagem de programação de alto nível.
    Ela é muito usada em automação, ciência de dados, inteligência artificial,
    desenvolvimento web e engenharia de software.

    Em projetos RAG, textos grandes precisam ser divididos em chunks menores
    para que possam ser transformados em embeddings e armazenados em bancos vetoriais.
    """ * 10

    chunker = TextChunker(
        chunk_size=300,
        chunk_overlap=50,
    )

    chunks = chunker.split(text)

    print(f"Total de chunks: {len(chunks)}")

    for index, chunk in enumerate(chunks, start=1):
        print(f"\n--- Chunk {index} ---")
        print(chunk)


if __name__ == "__main__":
    main()
