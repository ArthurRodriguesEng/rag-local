from importlib import import_module

from sqlalchemy import text

from app.config.database import Base, engine


def create_tables() -> None:
    """Cria todas as tabelas definidas nos Models."""

    import_module("app.models")

    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_tables()
