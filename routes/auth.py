import logging
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

from database.connections import get_db
from schemas.auth import RegisterRequest, LoginRequest, UserResponse
from database.crud.users import register_user, login_user

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── REGISTER ENDPOINT ────────────────────────────────────────────────────────
@router.post(
    "/register", 
    response_model=UserResponse, 
    status_code=status.HTTP_201_CREATED
)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    Endpoint to register a new user. 
    Uses dependency injection for database session management.
    """
    # Unpack the clean production-ready tuple from the CRUD layer
    success, message, user = register_user(db, name=req.name, email=req.email)
    
    if not success:
        logger.warning(f"Registration failed for {req.email}: {message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=message
        )
    
    # Returning the database object allows Pydantic (UserResponse) to serialize it automatically
    return user


# ─── LOGIN ENDPOINT ───────────────────────────────────────────────────────────
@router.post(
    "/login", 
    status_code=status.HTTP_200_OK
)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    Endpoint to authenticate an existing user via email.
    """
    # Clean the input data right at the gateway layer
    clean_email = req.email.strip().lower()
    
    success, message, user = login_user(db, email=clean_email)
    
    if not success:
        logger.warning(f"Login failed for {clean_email}: {message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,  # 401 is better than 404 for security
            detail=message
        )
        
    return user