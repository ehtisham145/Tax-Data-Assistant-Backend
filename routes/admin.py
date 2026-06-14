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


@router.get("/admin/users/{user_id}/conversations", response_model=list[HistoryItem])
def get_user_conversation_history(
    user_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Admin-only: kisi bhi user ki conversation history fetch karta hai.
    """
    try:
        conversations = get_history(db, user_id=user_id, limit=limit, offset=offset)
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Failed to fetch conversation history")

    if not conversations:
        raise HTTPException(status_code=404, detail="No conversations found for this user")

    return conversations

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