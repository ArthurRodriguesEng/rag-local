from app.services.document_loader import DocumentLoader


def main() -> None:
    loader = DocumentLoader()

    text = loader.load("documents/manual_python.txt")

    print("Texto extraído:")
    print(text)

    print("\nTotal de caracteres:")
    print(len(text))


if __name__ == "__main__":
    main()
