from pydantic import BaseModel,field_validator,EmailStr,Field
MAX_MESSAGE_LENGTH = 1000 

# ─── Request Model ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000)
    session_id: str
    email: EmailStr

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty.")
        if len(v) > MAX_MESSAGE_LENGTH:
            raise ValueError(f"Message too long. Max {MAX_MESSAGE_LENGTH} characters.")
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 8:
            raise ValueError("Invalid session_id.")
        return v