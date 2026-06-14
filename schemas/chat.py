from pydantic import BaseModel, Field, field_serializer
from datetime import datetime
from typing import Literal, Optional


class ChatRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    message: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None


class HistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    message: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime) -> str:
        return dt.isoformat() + "Z"


class HistoryResponse(BaseModel):
    success: bool
    history: list[HistoryItem]