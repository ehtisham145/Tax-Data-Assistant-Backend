import logging
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

from database_setup.connections import get_db
from schemas.auth import RegisterRequest, LoginRequest, UserResponse
from database_setup.crud.users import register_user, login_user

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── REGISTER ENDPOINT ────────────────────────────────────────────────────────
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user. The first registered user is granted admin rights.
    """
    success, message, user = register_user(db, name=req.name, email=req.email)

    if not success:
        logger.warning(f"Registration failed for {req.email}: {message}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return UserResponse(
        success=True,
        user_id=user.id,
        name=user.name,
        email=user.email,
    )


# ─── LOGIN ENDPOINT ───────────────────────────────────────────────────────────
@router.post(
    "/login",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate an existing user via email lookup.
    """
    success, message, user = login_user(db, email=req.email)

    if not success:
        logger.warning(f"Login failed for {req.email}: {message}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)

    return UserResponse(
        success=True,
        user_id=user.id,
        name=user.name,
        email=user.email,
    )