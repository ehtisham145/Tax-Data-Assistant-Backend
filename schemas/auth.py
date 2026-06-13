from pydantic import BaseModel, EmailStr

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr

class LoginRequest(BaseModel):
    email: EmailStr

class UserResponse(BaseModel):
    success: bool
    user_id: int
    name: str
    email: str
    is_admin: int