from pydantic import BaseModel, EmailStr, Field,field_validator
import re

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str
    @field_validator("phone")
    @classmethod
    def validate_uae_phone(cls, v: str) -> str:
        # Spaces/dashes hata do
        cleaned = re.sub(r"[\s\-]", "", v)
        
        # UAE formats:
        # +971501234567  → international
        # 00971501234567 → international (00)
        # 0501234567     → local
        pattern = r"^(\+971|00971|0)(50|51|52|54|55|56|58|2|3|4|6|7|9)\d{7}$"
        
        if not re.match(pattern, cleaned):
            raise ValueError(
                "Valid UAE phone number daalo — e.g. +971501234567 ya 0501234567"
            )
        return cleaned


class LoginRequest(BaseModel):
    email: EmailStr


class UserResponse(BaseModel):
    success: bool
    user_id: int
    name: str
    email: str
    phone : str
    is_existing: bool = False