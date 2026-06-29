from collections.abc import Generator

from sqlalchemy.orm import Session

from app.config.database import SessionLocal


def get_session() -> Generator[Session, None, None]:
    """Abre uma sessão do banco para uma requisição HTTP."""

    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
