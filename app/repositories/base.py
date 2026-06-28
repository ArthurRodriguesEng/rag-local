from typing import Any, TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository:
    """Classe base para todos os repositories."""

    def __init__(self, session: Session):
        self.session = session

    def commit(self) -> None:
        """Commit das alterações no banco de dados."""
        self.session.commit()

    def rollback(self) -> None:
        """Rollback das alterações no banco de dados."""
        self.session.rollback()

    def add(self, entity: T) -> None:
        """Adiciona um objeto à sessão."""
        self.session.add(entity)

    def delete(self, entity: T) -> None:
        """Remove um objeto da sessão."""
        self.session.delete(entity)

    def scalars(self, statement: Any):
        """Executa uma query e retorna múltiplos resultados."""
        return self.session.scalars(statement)

    def scalar(self, statement: Any):
        """Executa uma query e retorna um único resultado."""
        return self.session.scalar(statement)

    def refresh(self, entity: T) -> None:
        """Atualiza o estado de um objeto com os dados do banco."""
        self.session.refresh(entity)
