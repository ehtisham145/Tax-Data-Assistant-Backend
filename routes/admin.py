# routes/admin.py
from fastapi import APIRouter, HTTPException, Depends,Query
from sqlalchemy.orm import Session
from database_setup.connections import get_db
from database_setup.crud.users import get_all_users, delete_user, get_user_by_id, get_user_by_email
from utils.helpers import verify_admin_key
import logging
from utils.data_pipeline.pipeline import run_update_pipeline
from fastapi import status,BackgroundTasks
from database_setup.crud.conversation import get_history
from sqlalchemy.exc import SQLAlchemyError
from schemas.chat import HistoryItem
from database_setup.models import Conversation, Feedback 

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(verify_admin_key)])


@router.get("/users")
def list_users(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    users = get_all_users(db, limit=limit, offset=offset)
    return {
        "success": True,
        "users": [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "phone":u.phone,
                "created_at": u.created_at.isoformat() + "Z",
            }
            for u in users
        ],
    }


@router.delete("/users/{user_id}")
def remove_user(user_id: int, db: Session = Depends(get_db)):
    success, message = delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail=message)
    return {"success": True, "message": message}


@router.get("/users/by-id/{user_id}")
def admin_get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    result = get_user_by_id(db, user_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    result["created_at"] = result["created_at"].isoformat() + "Z"
    return result


@router.get("/users/by-email")
def admin_get_user_by_email(email: str, db: Session = Depends(get_db)):
    result = get_user_by_email(db, email)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    result["created_at"] = result["created_at"].isoformat() + "Z"
    return result



@router.get("/feedback")
def list_feedback(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    try:
        items = (
            db.query(Feedback)
            .order_by(Feedback.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
    except SQLAlchemyError as e:
        logger.error(f"DB error fetching feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch feedback")

    return {
        "success": True,
        "feedback": [
            {
                "id": f.id,
                "user_id": f.user_id,
                "user_message": f.user_message,
                "bot_response": f.bot_response,
                "rating": f.rating,
                "created_at": f.created_at.isoformat() + "Z",
            }
            for f in items
        ],
    }


@router.get("/feedback/stats")
def feedback_stats(db: Session = Depends(get_db)):
    try:
        total = db.query(Feedback).count()
        thumbs_up = db.query(Feedback).filter(Feedback.rating == "thumbs_up").count()
        thumbs_down = db.query(Feedback).filter(Feedback.rating == "thumbs_down").count()
    except SQLAlchemyError as e:
        logger.error(f"DB error fetching feedback stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch feedback stats")

    return {"total": total, "thumbs_up": thumbs_up, "thumbs_down": thumbs_down}


@router.get("/conversations/{user_id}")
def admin_get_conversations(user_id: int, limit: int = 200, offset: int = 0, db: Session = Depends(get_db)):
    try:
        messages = (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )
    except SQLAlchemyError as e:
        logger.error(f"DB error fetching conversations: user_id={user_id} - {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch conversation history")

    return {
        "success": True,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "message": m.message,
                "created_at": m.created_at.isoformat() + "Z",
            }
            for m in messages
        ],
    }



# ─── Refresh Data Endpoint ────────────────────────────────────────────────────

async def run_update_pipeline_wrapper():
    """Background wrapper: runs the pipeline and logs the final result."""
    try:
        result = await run_update_pipeline()
        logger.info(f"Background pipeline finished. Result: {result}")
    except Exception as e:
        logger.critical(f"Background pipeline crashed unexpectedly: {e}", exc_info=True)


@router.post("/refresh-data", status_code=status.HTTP_202_ACCEPTED)
async def refresh_training_data(background_tasks: BackgroundTasks):
    """
    Trigger the data update pipeline in the background.
    Returns 202 Accepted immediately so the request doesn't time out.
    """
    logger.info("Admin triggered data refresh pipeline")
    background_tasks.add_task(run_update_pipeline_wrapper)

    return {
        "status": "accepted",
        "message": "Data refresh pipeline triggered in the background. Check logs for progress.",
    }