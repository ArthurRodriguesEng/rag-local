from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.message import Message
from app.repositories.base import BaseRepository


class MessageRepository(BaseRepository):
    """Repository responsável pelo histórico de mensagens."""

    def __init__(self, session: Session):
        super().__init__(session)

    def create(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
    ) -> Message:
        """Cria uma mensagem em uma conversa."""

        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        self.add(message)

        return message

    def list_by_conversation(
        self,
        conversation_id: UUID,
        limit: int | None = None,
    ) -> list[Message]:
        """Lista mensagens de uma conversa em ordem cronológica."""

        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )

        if limit is not None:
            recent_ids = (
                select(Message.id)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.desc())
                .limit(limit)
                .subquery()
            )
            statement = (
                select(Message)
                .where(Message.id.in_(select(recent_ids.c.id)))
                .order_by(Message.created_at.asc())
            )

        return list(self.scalars(statement))
