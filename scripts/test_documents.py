from app.config.database import SessionLocal
from app.models.document import Document


def main() -> None:
    session = SessionLocal()

    try:
        document = Document(filename="manual_python.pdf")

        session.add(document)
        session.commit()

        print(document.id)

    finally:
        session.close()


if __name__ == "__main__":
    main()
