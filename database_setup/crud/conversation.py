from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError,SQLAlchemyError
from database_setup.models import Conversation
import logging

logger = logging.getLogger(__name__)

def save_message(db: Session, user_id: int, role: str, message: str) -> bool:
    try:
        msg = Conversation(user_id=user_id, role=role, message=message)
        db.add(msg)
        db.commit()
        logger.info(f"Message saved: user_id={user_id} role={role}")
        return True
    
    #Integrity Error Occurs when we break a database rule or constraint
    except IntegrityError as e:
        logger.error(f"Save message failed: {e}")
        raise

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"DB error saving message: user_id={user_id} role={role} - {e}")
        raise


def get_history(db: Session, user_id: int, limit: int = 50, offset: int = 0) -> list[Conversation]:
    try:
        return (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )
    except SQLAlchemyError as e:
        logger.error(f"DB error fetching history: user_id={user_id} - {e}")
        raise