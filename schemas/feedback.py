from pydantic import BaseModel
from datetime import datetime
from typing import Literal

class FeedbackRequest(BaseModel):
    user_id: int
    user_message: str
    bot_response: str
    rating: Literal["thumbs_up", "thumbs_down"]

class FeedbackItem(BaseModel):
    id: int
    user_message: str
    bot_response: str
    rating: str
    created_at: datetime

class FeedbackResponse(BaseModel):
    success: bool
    feedbacks: list[FeedbackItem]