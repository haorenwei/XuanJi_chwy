from datetime import datetime, timedelta

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message


class ConversationService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_active(self, user_id: int) -> Conversation:
        conv = (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user_id, Conversation.is_active == True)
            .order_by(desc(Conversation.updated_at))
            .first()
        )
        if conv:
            return conv
        conv = Conversation(user_id=user_id, title="New Conversation", is_active=True)
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def create_conversation(self, user_id: int, title: str | None = None) -> Conversation:
        # Deactivate current active conversations
        self.db.query(Conversation).filter(
            Conversation.user_id == user_id, Conversation.is_active == True
        ).update({"is_active": False})
        conv = Conversation(
            user_id=user_id,
            title=title or "New Conversation",
            is_active=True,
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def list_conversations(self, user_id: int, page: int = 1, limit: int = 20) -> list[Conversation]:
        offset = (page - 1) * limit
        return (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(desc(Conversation.updated_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_conversation(self, conversation_id: int, user_id: int) -> Conversation | None:
        return (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
            .first()
        )

    def add_message(
        self,
        conversation_id: int,
        user_id: int,
        role: str,
        content: str,
        metadata_json: str | None = None,
        emotion_snapshot: str | None = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            content=content,
            metadata_json=metadata_json,
            emotion_snapshot=emotion_snapshot,
        )
        self.db.add(msg)
        # Increment message count
        self.db.query(Conversation).filter(Conversation.id == conversation_id).update(
            {"message_count": Conversation.message_count + 1}
        )
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_messages(
        self, conversation_id: int, limit: int = 50, before_id: int | None = None
    ) -> list[Message]:
        query = self.db.query(Message).filter(Message.conversation_id == conversation_id)
        if before_id:
            query = query.filter(Message.id < before_id)
        return query.order_by(desc(Message.id)).limit(limit).all()[::-1]

    def get_recent_messages_for_context(self, user_id: int, limit: int = 20) -> list[Message]:
        """Get recent messages across active conversation for context injection."""
        active_conv = (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user_id, Conversation.is_active == True)
            .first()
        )
        if not active_conv:
            return []
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == active_conv.id)
            .order_by(desc(Message.id))
            .limit(limit)
            .all()
        )[::-1]

    def get_recent_messages(self, user_id: int, days: int = 3) -> list[Message]:
        """Get all messages for a user within the last N days across all conversations."""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = today_start - timedelta(days=days - 1)  # 包含今天在内的N天
        return (
            self.db.query(Message)
            .filter(Message.user_id == user_id, Message.created_at >= start_date)
            .order_by(asc(Message.created_at))
            .all()
        )

    def mark_messages_summarized(self, message_ids: list[int]) -> None:
        if not message_ids:
            return
        self.db.query(Message).filter(Message.id.in_(message_ids)).update(
            {"is_summarized": True}, synchronize_session=False
        )
        self.db.commit()

    def update_conversation(self, conversation_id: int, user_id: int, **kwargs) -> Conversation | None:
        conv = self.get_conversation(conversation_id, user_id)
        if not conv:
            return None
        for key, value in kwargs.items():
            if hasattr(conv, key):
                setattr(conv, key, value)
        self.db.commit()
        self.db.refresh(conv)
        return conv
