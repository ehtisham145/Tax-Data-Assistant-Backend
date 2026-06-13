from fastapi import APIRouter, HTTPException,status,Depends
from fastapi import BackgroundTasks
from database.connections import get_db
from database.crud.users import get_all_users, delete_user,is_admin
from main import reload_retriever
from utils.helpers import verify_admin
from utils.pipeline import run_update_pipeline
import logging

logger=logging.getLogger(__name__)
router = APIRouter()


@router.get("/users/{requester_id}")
def list_users(requester_id: int):
    with get_db() as db:
        if not is_admin(db, requester_id):
            raise HTTPException(status_code=403, detail="Permission denied")
        users = get_all_users(db)
        return {
            "success": True,
            "users": [
                {"id": u.id, "name": u.name, "email": u.email,
                 "is_admin": u.is_admin, "created_at": u.created_at}
                for u in users
            ]
        }


@router.delete("/user/{requester_id}/{user_id}")
def remove_user(requester_id: int, user_id: int):
    with get_db() as db:
        if not is_admin(db, requester_id):
            raise HTTPException(status_code=403, detail="Permission denied")
        result = delete_user(db, user_id)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])
        return result

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

