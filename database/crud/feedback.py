from sqlalchemy.orm import Session
from database.models import Feedback
import logging

logger = logging.getLogger(__name__)

def save_feedback(db: Session, user_id: int, user_message: str, 
                  bot_response: str, rating: str) -> dict:
    try:
        fb = Feedback(user_id=user_id, user_message=user_message,
                      bot_response=bot_response, rating=rating)
        db.add(fb)
        db.flush()
        logger.info(f"✅ Feedback saved: user_id={user_id} rating={rating}")
        return {"success": True, "message": "Feedback saved"}
    except Exception as e:
        logger.error(f"❌ Feedback failed: {e}")
        raise

def get_feedback(db: Session, user_id: int) -> list:
    return (
        db.query(Feedback)
        .filter(Feedback.user_id == user_id)
        .order_by(Feedback.created_at.desc())
        .all()
    )