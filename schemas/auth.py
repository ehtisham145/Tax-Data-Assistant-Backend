from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr


class UserResponse(BaseModel):
    success: bool
    user_id: int
    name: str
    email: str