from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError,IntegrityError
from database_setup.models import Feedback
import logging

logger = logging.getLogger(__name__)

def save_feedback(db: Session, user_id: int, user_message: str, 
                  bot_response: str, rating: str) -> dict:
    try:
        fb = Feedback(user_id=user_id, user_message=user_message,
                      bot_response=bot_response, rating=rating)
        db.add(fb)
        db.commit()
        logger.info(f"✅ Feedback saved: user_id={user_id} rating={rating}")
        return {"success": True, "message": "Feedback saved"}
    
    except InterruptedError as e:
        db.rollback()
        logger.error(f"Integrity error saving feedback: user_id={user_id} rating={rating} - {e}")
        raise

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"DB error saving feedback: user_id={user_id} rating={rating} - {e}")
        raise

    
def get_feedback(db: Session, user_id: int, limit: int = 50, offset: int = 0) -> list[Feedback]:
    try:
        return (
            db.query(Feedback)
            .filter(Feedback.user_id == user_id)
            .order_by(Feedback.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
    except SQLAlchemyError as e:
        logger.error(f"DB error fetching feedback: user_id={user_id} - {e}")
        raise