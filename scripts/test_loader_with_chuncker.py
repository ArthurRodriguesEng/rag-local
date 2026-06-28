from app.services.document_loader import DocumentLoader
from app.services.text_chunker import RecursiveTextChunker


def main() -> None:
    loader = DocumentLoader()
    chunker = RecursiveTextChunker(
        chunk_size=150,
        chunk_overlap=30,
    )

    text = loader.load("documents/manual_python.txt")

    chunks = chunker.split(text)

    print(f"Total de caracteres: {len(text)}")
    print(f"Total de chunks: {len(chunks)}")

    for index, chunk in enumerate(chunks, start=1):
        print(f"\n--- Chunk {index} ---")
        print(chunk)
        print(f"Tamanho: {len(chunk)}")


if __name__ == "__main__":
    main()
