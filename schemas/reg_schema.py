from pydantic import BaseModel,EmailStr,field_validator
from typing import List

#--------------------------Register Schema---------------------------------
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr  # Validates email format automatically
    session_id: str


    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters.")
        if len(v) > 100:
            raise ValueError("Name must not exceed 100 characters.")
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 8:
            raise ValueError("Invalid session_id.")
        return v

class RegisterResponse(BaseModel):
    status: str
    message: str



#--------------------------------User Schema------------------------------------

class UserOut(BaseModel):
    session_id: str
    name: str
    email: str
    created_at: str


class UsersResponse(BaseModel):
    total: int
    users: List[UserOut]