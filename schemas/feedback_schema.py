from pydantic import BaseModel, Field
from typing import Literal
from typing import List

class FeedbackRequest(BaseModel):
    session_id: str = Field(..., max_length=100, examples=["session_abc123"])
    user_message: str = Field(..., max_length=2000) # Limit text to 2000 chars
    bot_response: str = Field(..., max_length=4000) # Limit bot response 
    rating: Literal['thumbs_up', 'thumbs_down']    # Sirf yahi do values allowed hain

class FeedbackPaginatedResponse(BaseModel):
    total: int = Field(..., description="Total number of feedback entries available")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Number of items returned per page")
    feedback: List[FeedbackRequest]


class FeedbackStatsResponse(BaseModel):
    total: int = Field(..., description="Total number of feedback submissions")
    thumbs_up: int = Field(..., description="Total count of positive feedback")
    thumbs_down: int = Field(..., description="Total count of negative feedback")