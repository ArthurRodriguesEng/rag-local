from app.services.text_chunker import RecursiveTextChunker


def main() -> None:
    text = """
    Python é uma linguagem de programação de alto nível.

    Ela é usada em automação, ciência de dados, inteligência artificial
    e desenvolvimento web.

    Em projetos RAG, textos grandes precisam ser divididos em chunks menores.
    Cada chunk recebe um embedding e é salvo no banco vetorial.

    Quando o usuário faz uma pergunta, o sistema busca os chunks mais relevantes
    e usa esses trechos como contexto para gerar uma resposta.
    """ * 5

    chunker = RecursiveTextChunker(
        chunk_size=400,
        chunk_overlap=80,
    )

    chunks = chunker.split(text)

    print(f"Total de chunks: {len(chunks)}")

    for index, chunk in enumerate(chunks, start=1):
        print(f"\n--- Chunk {index} ---")
        print(chunk)
        print(f"Tamanho: {len(chunk)}")


if __name__ == "__main__":
    main()
