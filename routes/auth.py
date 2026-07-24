import logging
from fastapi import APIRouter, HTTPException, Depends, status, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from database_setup.connections import get_db
from schemas.auth import RegisterRequest ,UserResponse
from database_setup.crud.users import register_user, login_user

logger = logging.getLogger(__name__)
router = APIRouter()

limiter = Limiter(key_func=get_remote_address)


def mask_email(email: str) -> str:
    """Mask email for safe logging, e.g. jo***@gmail.com"""
    try:
        local, domain = email.split("@")
        masked_local = local[:2] + "***" if len(local) > 2 else "***"
        return f"{masked_local}@{domain}"
    except Exception:
        return "***"


# ─── REGISTER ENDPOINT ────────────────────────────────────────────────────────
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def register(request: Request, req: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user. The first registered user is granted admin rights.
    Rate-limited to prevent spam/bot registrations.
    """
    success, message, user = register_user(db, name=req.name, email=req.email, phone=req.phone)

    if not success:
        logger.warning(f"Registration failed for {mask_email(req.email)}: {message}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return UserResponse(
        success=True,
        user_id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        is_existing=(message == "existing"),
    )