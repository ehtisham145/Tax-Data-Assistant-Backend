from fastapi import APIRouter, HTTPException, Depends, Request
from starlette.concurrency import run_in_threadpool
from slowapi import Limiter
from slowapi.util import get_remote_address
from database.users import insert_user
from schemas.reg_schema import RegisterRequest, RegisterResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=RegisterResponse, status_code=200)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest) -> RegisterResponse:
    """Register a new user with name, email, and session_id."""
    try:
        inserted, user_name = await run_in_threadpool(
            insert_user, body.session_id, body.name, body.email
        )
    except Exception as e:
        logger.error(f"❌ DB error during registration for {body.email}: {e}")
        raise HTTPException(status_code=500, detail="Registration failed. Please try again.")

    if not inserted:
        logger.info(f"↩️  Already registered: {body.email}")
        return RegisterResponse(
            status="already_registered",
            message=f"Welcome back {user_name}! You are already registered.",
        )

    logger.info(f"✅ New user registered: {body.email}")
    return RegisterResponse(
        status="registered",
        message=f"Welcome {body.name}! You can now start chatting.",
    )