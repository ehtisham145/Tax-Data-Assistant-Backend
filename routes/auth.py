from fastapi import APIRouter
from pydantic import BaseModel, EmailStr
from database import insert_user, get_all_users
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr  # Validates email format automatically
    session_id: str

@router.post("/register")
def register(request: RegisterRequest):
    """Register a new user with name, email, and session_id."""
    try:
        inserted, user_name = insert_user(
            request.session_id, request.name, request.email
        )

        if not inserted:
            return {
                "status": "already_registered",
                "message": f"Welcome back {user_name}! You are already registered."
            }

        logger.info(f"✅ New user registered: {request.email}")
        return {
            "status": "registered",
            "message": f"Welcome {request.name}! You can now start chatting."
        }

    except Exception as e:
        logger.error(f"❌ Registration error: {e}")
        raise

@router.get("/users")
def get_users():
    """Get all registered users — for admin use only."""
    try:
        users = get_all_users()
        return {
            "total": len(users),
            "users": [
                {
                    "session_id": u[0],
                    "name": u[1],
                    "email": u[2],
                    "created_at": u[3]
                }
                for u in users
            ]
        }
    except Exception as e:
        logger.error(f"❌ Error fetching users: {e}")
        raise