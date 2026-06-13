from fastapi import APIRouter, HTTPException
from schemas.feedback import FeedbackRequest
from database.connections import get_db
from database.crud.feedback import save_feedback, get_feedback

router = APIRouter(prefix="/feedback", tags=["Feedback"])

@router.post("/submit")
def submit(req: FeedbackRequest):
    with get_db() as db:
        result = save_feedback(db, req.user_id, req.user_message,
                               req.bot_response, req.rating)
        return result

@router.get("/get/{user_id}")
def fetch(user_id: int):
    with get_db() as db:
        items = get_feedback(db, user_id)
        return {
            "success": True,
            "feedbacks": [
                {"id": f.id, "user_message": f.user_message,
                 "bot_response": f.bot_response, "rating": f.rating,
                 "created_at": f.created_at}
                for f in items
            ]
        }