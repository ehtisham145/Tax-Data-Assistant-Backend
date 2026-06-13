from pydantic import BaseModel
from datetime import datetime

class ChatRequest(BaseModel):
    user_id: int
    message: str

class ChatResponse(BaseModel):
    success: bool
    response: str

class HistoryItem(BaseModel):
    role: str
    message: str
    created_at: datetime

class HistoryResponse(BaseModel):
    success: bool
    history: list[HistoryItem]