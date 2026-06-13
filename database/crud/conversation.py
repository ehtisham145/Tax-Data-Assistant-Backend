from sqlalchemy.orm import Session
from database.models import Conversation
import logging

logger = logging.getLogger(__name__)

def save_message(db: Session, user_id: int, role: str, message: str) -> bool:
    try:
        msg = Conversation(user_id=user_id, role=role, message=message)
        db.add(msg)
        db.flush()
        logger.info(f"✅ Message saved: user_id={user_id} role={role}")
        return True
    except Exception as e:
        logger.error(f"❌ Save message failed: {e}")
        raise

def get_history(db: Session, user_id: int) -> list:
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.asc())
        .all()
    )