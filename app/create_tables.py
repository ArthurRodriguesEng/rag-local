from app.config.database import Base, engine

# Importa todos os models
from app.models.document import Document


def create_tables() -> None:
    """Cria todas as tabelas definidas nos Models."""
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_tables()
