import logging
from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from schemas.feedback import FeedbackRequest, FeedbackResponse, FeedbackItem
from database_setup.connections import get_db
from database_setup.crud.feedback import save_feedback, get_feedback

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/submit", status_code=status.HTTP_201_CREATED)
def submit(req: FeedbackRequest, db: Session = Depends(get_db)):
    try:
        result = save_feedback(
            db,
            req.user_id,
            req.user_message,
            req.bot_response,
            req.rating,
        )
        return result
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user_id or rating value",
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save feedback",
        )


@router.get("/get/{user_id}", response_model=FeedbackResponse)
def fetch(
    user_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    try:
        items = get_feedback(db, user_id, limit=limit, offset=offset)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch feedback",
        )

    return FeedbackResponse(
        success=True,
        feedbacks=[
            FeedbackItem(
                id=f.id,
                user_message=f.user_message,
                bot_response=f.bot_response,
                rating=f.rating,
                created_at=f.created_at,
            )
            for f in items
        ],
    )