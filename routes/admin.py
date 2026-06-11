import sqlite3
import logging
from typing import Optional
from database.connections import get_db
from fastapi import APIRouter, HTTPException,status,BackgroundTasks,Depends
from utils.pipeline import run_update_pipeline
from utils.config import ADMIN_SECRET
from main import reload_retriever


logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Admin Auth Helper ────────────────────────────────────────────────────────

def verify_admin(secret: str):
    """Check admin secret — raise 403 if wrong."""
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="❌ Not allowed! Admin only.")


# ─── DB Helper Functions ──────────────────────────────────────────────────────

def get_user_by_session(session_id: str) -> Optional[tuple]:
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT name, email FROM users WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            return tuple(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"❌ Error fetching user by session [{session_id}]: {e}")
        raise


def get_user_by_email(email: str) -> Optional[tuple]:
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT name, email FROM users WHERE email = ?", (email,)
            ).fetchone()
            return tuple(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"❌ Error fetching user by email [{email}]: {e}")
        return None


def get_all_users() -> list:
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT session_id, name, email, created_at FROM users ORDER BY created_at DESC"
            ).fetchall()
            return [tuple(r) for r in rows]
    except sqlite3.Error as e:
        logger.error(f"❌ Error fetching all users: {e}")
        raise


def get_conversation_history(session_id: str) -> list:
    try:
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT role, message, created_at
                FROM conversations
                WHERE session_id = ?
                ORDER BY created_at ASC
                """,
                (session_id,),
            ).fetchall()
            return [tuple(r) for r in rows]
    except sqlite3.Error as e:
        logger.error(f"❌ Error fetching history [{session_id}]: {e}")
        raise


def delete_conversation(session_id: str) -> None:
    try:
        with get_db() as conn:
            conn.execute(
                "DELETE FROM conversations WHERE session_id = ?",
                (session_id,),
            )
        logger.info(f"✅ Conversation deleted for session: {session_id}")
    except sqlite3.Error as e:
        logger.error(f"❌ Error deleting conversation [{session_id}]: {e}")
        raise


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