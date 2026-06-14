from pydantic import BaseModel, Field, field_serializer
from datetime import datetime
from typing import Literal


class FeedbackRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    user_message: str = Field(..., min_length=1, max_length=4000)
    bot_response: str = Field(..., min_length=1, max_length=4000)
    rating: Literal["thumbs_up", "thumbs_down"]


class FeedbackItem(BaseModel):
    id: int
    user_message: str
    bot_response: str
    rating: Literal["thumbs_up", "thumbs_down"]
    created_at: datetime

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime) -> str:
        return dt.isoformat() + "Z"


class FeedbackResponse(BaseModel):
    success: bool
    feedbacks: list[FeedbackItem]