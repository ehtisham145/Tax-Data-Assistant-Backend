from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.concurrency import run_in_threadpool
from database.users import insert_user, get_all_users
from typing import Optional
import logging
from schemas.reg_schema import RegisterRequest,RegisterResponse,UsersResponse,UserOut
import os

logger = logging.getLogger(__name__)
router = APIRouter()
limiter=Limiter(key=get_remote_address)

"""In SlowAPI, the get_remote_address function inside the slowapi.util module is 
used to identify the client by retrieving their IP address.
Since SlowAPI needs a way to track who is making requests so it can 
block them if they exceed the limit, 
it uses this function as a "key" to keep count of the requests"""

# ─── Simple API Key Auth for Admin Endpoint ──────────────────────────────────

API_KEY = os.getenv("ADMIN_KEY")  

def verify_admin(request: Request):
    key = request.headers.get("X-Admin-Key")
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid admin key.")


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post(
        "/register",
        response_model=RegisterResponse,
        status_code=200,
        summary="Register a new user"
)

@router.post("/register", response_model=RegisterResponse)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest) -> RegisterResponse:
    """Register a new user with name, email, and session_id."""
    try:
        """Await keyword allow you to process remaining while
        processing this Request in backgorun instead of freezing the server"""
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

    logger.info(f"✅ New user registered: {request.email}")

    return RegisterResponse(
        status="registered",
        message=f"Welcome {body.name}! You can now start chatting.",
    )



@router.get(
        "/users",
        response_model=UsersResponse,
        summary="Get all users (Admin only)",
        dependencies=[Depends(verify_admin)]
        )

async def get_users():
    """Get all registered users — for admin use only."""
    try:
        users = await run_in_threadpool(get_all_users)
    
    except Exception as e:
        logger.error(f"❌ Error fetching users: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch users.")
    
    return UsersResponse(
        total=len(users),
        users=[
            UserOut(
                session_id=u[0],
                name=u[1],
                email=u[2],
                created_at=str(u[3]),
            )
            for u in users
        ],
    )