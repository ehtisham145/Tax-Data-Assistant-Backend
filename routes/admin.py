import sqlite3
import logging
from typing import Optional
from database.connections import get_db
from fastapi import APIRouter, HTTPException,status,BackgroundTasks,Depends
from utils.pipeline import run_update_pipeline
from utils.config import ADMIN_SECRET
from main import reload_retriever
# Add FeedbackResponse to import
from schemas.feedback_schema import FeedbackResponse, FeedbackPaginatedResponse, FeedbackStatsResponse
from fastapi import Query
from starlette.concurrency import run_in_threadpool
from utils.helpers import verify_admin
from database.users import get_all_users,get_user_by_session,get_user_by_email
from database.conversations import get_conversation_history,delete_conversation
from database.feedback import get_all_feedback,get_feedback_stats

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Admin API Endpoints ──────────────────────────────────────────────────────

@router.get("/users")
def api_get_all_users(secret: str):
    """Sare users dekho. Usage: /admin/users?secret=PASSWORD"""
    verify_admin(secret)
    users = get_all_users()
    return {
        "total_users": len(users),
        "users": [
            {
                "session_id": u[0],
                "name": u[1],
                "email": u[2],
                "created_at": u[3],
            }
            for u in users
        ],
    }


@router.get("/users/session/{session_id}")
def api_get_user_by_session(session_id: str, secret: str):
    """Session ID se user dhundho. Usage: /admin/users/session/ID?secret=PASSWORD"""
    verify_admin(secret)
    user = get_user_by_session(session_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"name": user[0], "email": user[1]}


@router.get("/users/email/{email}")
def api_get_user_by_email(email: str, secret: str):
    """Email se user dhundho. Usage: /admin/users/email/EMAIL?secret=PASSWORD"""
    verify_admin(secret)
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"name": user[0], "email": user[1]}


@router.get("/conversations/{session_id}")
def api_get_conversations(session_id: str, secret: str):
    """Kisi session ki poori conversation dekho. Usage: /admin/conversations/ID?secret=PASSWORD"""
    verify_admin(secret)
    history = get_conversation_history(session_id)
    return {
        "session_id": session_id,
        "total_messages": len(history),
        "messages": [
            {
                "role": h[0],
                "message": h[1],
                "created_at": h[2],
            }
            for h in history
        ],
    }


@router.delete("/conversations/{session_id}")
def api_delete_conversation(session_id: str, secret: str):
    """Kisi session ki conversation delete karo. Usage: /admin/conversations/ID?secret=PASSWORD"""
    verify_admin(secret)
    delete_conversation(session_id)
    return {"status": "✅ Conversation deleted!", "session_id": session_id}


@router.delete("/users/session/{session_id}")
def api_delete_user(session_id: str, secret: str):
    """User delete karo. Usage: /admin/users/session/ID?secret=PASSWORD"""
    verify_admin(secret)
    try:
        with get_db() as conn:
            conn.execute(
                "DELETE FROM users WHERE session_id = ?", (session_id,)
            )
        return {"status": "✅ User deleted!", "session_id": session_id}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# ─── Refresh Data Endpoint ────────────────────────────────────────────────────

async def run_update_pipeline_wrapper():
    """Wrapper function jo pipeline chalayegi aur uska result end me log karegi."""
    try:
        result = await run_update_pipeline()
        logger.info(f"📊 Background Pipeline Finished. Result: {result}")

        # ─── Reload retriever after fresh data ingested ───────────────────
        if result["status"] == "updated":
            reloaded = await reload_retriever()
            if reloaded:
                logger.info("✅ Retriever reloaded with fresh ChromaDB data!")
            else:
                logger.error("❌ Retriever reload failed — restart app manually!")

    except Exception as e:
        logger.critical(f"💥 Background Pipeline crashed unexpectedly: {e}", exc_info=True)


# ─── Refresh Data Endpoint ────────────────────────────────────────────────────
@router.post("/refresh-data", status_code=status.HTTP_202_ACCEPTED)
async def refresh_training_data(
    background_tasks: BackgroundTasks,
    _=Depends(verify_admin)
):
    """
    Trigger the auto-update pipeline safely in the background.
    Returns 202 Accepted immediately so the request doesn't timeout.
    """
    logger.info("🎬 Admin verified successfully. Triggering data refresh pipeline...")

    background_tasks.add_task(run_update_pipeline_wrapper)

    return {
        "status": "accepted",
        "message": "Data refresh pipeline has been triggered in the background. Check logs for progress."
    }

# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get(
    "/feedback",
    response_model=FeedbackPaginatedResponse,
    status_code=status.HTTP_200_OK,
    summary="Get paginated user feedback",
)
async def view_all_feedback(
    page: int = Query(1, ge=1, description="Page number to retrieve"),
    limit: int = Query(50, ge=1, le=100, description="Number of items per page"),
    _=Depends(verify_admin)
):
    """
    Fetch user feedback with pagination to protect server performance.
    
    - **page**: Current page (Starts at 1)
    - **limit**: Items per page (Max 100)
    """
    try:
        # Note: You should update your underlying `get_all_feedback` function 
        # to accept limit and offset parameters for standard SQL pagination (LIMIT/OFFSET).
        offset = (page - 1) * limit
        
        # Simulating passing pagination parameters down to the threadpool function
        feedback_records, total_count = await run_in_threadpool(get_all_feedback, limit=limit, offset=offset)
        
        return {
            "total": total_count,
            "page": page,
            "limit": limit,
            "feedback": [
                {
                    "session_id": f[0],
                    "user_message": f[1],
                    "bot_response": f[2],
                    "rating": f[3],
                    "created_at": f[4],
                }
                for f in feedback_records
            ],
        }
    except Exception as e:
        logger.error(f"❌ Error fetching feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An error occurred while fetching feedback records."
        )


@router.get(
    "/feedback/stats",
    response_model=FeedbackStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get feedback metrics",
)
async def view_feedback_stats(_=Depends(verify_admin)):
    """
    Retrieve aggregated metrics for thumbs up and thumbs down counts.
    """
    try:
        stats = await run_in_threadpool(get_feedback_stats)
        
        # Defensive check against None or missing keys from the database function
        return {
            "total": stats.get("total", 0),
            "thumbs_up": stats.get("thumbs_up", 0),
            "thumbs_down": stats.get("thumbs_down", 0),
        }
    except Exception as e:
        logger.error(f"❌ Error fetching feedback stats: {e}", exc_info=True)
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An error occurred while aggregating feedback statistics."
        )