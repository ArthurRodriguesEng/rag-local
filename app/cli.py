from sqlalchemy import text

from app.config.database import Base, engine


def init_db() -> None:
    """Inicializa o banco de dados da aplicação."""

    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
