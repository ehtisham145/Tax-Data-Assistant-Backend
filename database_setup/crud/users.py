import logging
from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session
from database_setup.models import User


logger = logging.getLogger(__name__)


# ─── REGISTER USER ───────────────────────────────────────────────────────────
def register_user(db: Session, name: str, email: str,phone:str) -> Tuple[bool, str, Optional[User]]:
    """
    Registers a new user. Assigns admin rights to the very first user in the database.

    Returns:
        Tuple[bool, str, Optional[User]]: (success_status, message, user_object)
    """
    email = email.strip().lower()

    try:
        existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing:
            logger.info(f"Email already registered, returning existing user: {email}")
            return True, "existing", existing

        new_user = User(name=name, email=email,phone=phone)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info(f"User registered: id={new_user.id}")
        return True, "registered", new_user

    except IntegrityError:
        # Race: email got inserted between our check and commit — fetch and return it.
        db.rollback()
        existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing:
            logger.info(f"Email already registered (race), returning existing user: {email}")
            return True, "existing", existing
        logger.warning(f"Registration integrity error for {email}")
        return False, "Registration failed", None
    
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"DB error during registration for {email}: {e}", exc_info=True)
        raise


# ─── LOGIN USER ──────────────────────────────────────────────────────────────
def login_user(db: Session, email: str) -> Tuple[bool, str, Optional[User]]:
    """
    Validates user existence via email.

    Returns:
        Tuple[bool, str, Optional[User]]: (success_status, message, user_object)
    """
    email = email.strip().lower()

    try:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if not user:
            logger.warning(f"Login failed - email not found: {email}")
            return False, "Email not found. Please register first.", None

        logger.info(f"User logged in: id={user.id}")
        return True, "Login successful", user

    except SQLAlchemyError as e:
        logger.error(f"DB error during login for {email}: {e}", exc_info=True)
        raise


# ─── GET ALL USERS ───────────────────────────────────────────────────────────
def get_all_users(db: Session, limit: int = 100, offset: int = 0) -> List[User]:
    """
    Fetches user records from the database with pagination.
    """
    try:
        result = db.execute(select(User).order_by(User.id.asc()).limit(limit).offset(offset))
        return list(result.scalars().all())
    
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch users: {e}", exc_info=True)
        raise



# ─── GET USER BY EMAIL ───────────────────────────────────────────────────────
def get_user_by_email(db: Session, email: str) -> dict:
    """
    Fetches a single user by email address. Used by admin for lookups.
    """
    email = email.strip().lower()

    try:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

        if not user:
            logger.warning(f"User not found by email: {email}")
            return {"success": False, "message": "User not found"}

        return {
            "success": True,
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "phone" : user.phone,
            "created_at": user.created_at,
        }

    except SQLAlchemyError as e:
        logger.error(f"Fetch failed for email={email}: {e}", exc_info=True)
        raise


# ─── GET USER BY ID ──────────────────────────────────────────────────────────
def get_user_by_id(db: Session, user_id: int) -> dict:
    """
    Fetches a single user by primary key ID.
    """
    try:
        user = db.get(User, user_id)

        if not user:
            logger.warning(f"User not found: id={user_id}")
            return {"success": False, "message": "User not found"}

        return {
            "success": True,
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "phone":user.phone,
            "created_at": user.created_at,
        }

    except SQLAlchemyError as e:
        logger.error(f"Fetch failed for user_id={user_id}: {e}", exc_info=True)
        raise


# ─── DELETE USER ─────────────────────────────────────────────────────────────
def delete_user(db: Session, user_id: int) -> Tuple[bool, str]:
    """
    Deletes a user record by primary key ID. Cascades to conversations and feedback.

    Returns:
        Tuple[bool, str]: (success_status, message)
    """
    try:
        user = db.get(User, user_id)
        if not user:
            logger.warning(f"Delete failed - user not found: id={user_id}")
            return False, "User not found"

        db.delete(user)
        db.commit()

        logger.info(f"User deleted: id={user_id}")
        return True, f"User {user_id} deleted successfully"

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to delete user {user_id}: {e}", exc_info=True)
        raise