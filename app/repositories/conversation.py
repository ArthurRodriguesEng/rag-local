from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository):
    """Repository responsável por conversas."""

    def __init__(self, session: Session):
        super().__init__(session)

    def create(self, title: str | None = None) -> Conversation:
        """Cria uma nova conversa."""

        conversation = Conversation(title=title)
        self.add(conversation)

        return conversation

    def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        """Busca uma conversa pelo ID."""

        statement = select(Conversation).where(Conversation.id == conversation_id)

        return self.scalar(statement)

    def list_recent(self, limit: int = 20) -> list[Conversation]:
        """Lista conversas recentes."""

        statement = (
            select(Conversation)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )

        return list(self.scalars(statement))
