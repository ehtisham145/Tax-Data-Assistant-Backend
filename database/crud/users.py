import logging
from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from database.models import User

logger = logging.getLogger(__name__)

# ─── REGISTER USER ───────────────────────────────────────────────────────────
def register_user(db: Session, name: str, email: str) -> Tuple[bool, str, Optional[User]]:
    """
    Registers a new user. Assigns admin rights to the very first user in the database.
    
    Returns:
        Tuple[bool, str, Optional[User]]: (success_status, message, user_object)
    """
    try:
        # 1. Use SQLAlchemy 2.0 select syntax to check existence
        existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing:
            logger.warning(f"↩️ Registration rejected — Email already exists: {email}")
            return False, "Email already registered", None

        # 2. Optimized count query using func.count() instead of loading all rows
        total_users = db.execute(select(func.count()).select_from(User)).scalar_one()
        
        # 3. Assign admin privilege if it's the first user (using True/False flags for production)
        is_admin = True if total_users == 0 else False

        # 4. Create and save the user
        new_user = User(name=name, email=email, is_admin=is_admin)
        db.add(new_user)
        db.commit()          # Safely write data to disk permanently
        db.refresh(new_user) # Pull the generated ID from the DB back into the object

        logger.info(f"✅ User registered successfully: {email} (ID: {new_user.id})")
        return True, "Registration successful", new_user

    except Exception as e:
        db.rollback()  # CRITICAL: Revert database state if any operation fails
        logger.error(f"❌ Database error during registration for {email}: {str(e)}", exc_info=True)
        raise



# ─── LOGIN USER ──────────────────────────────────────────────────────────────
def login_user(db: Session, email: str) -> Tuple[bool, str, Optional[User]]:
    """
    Validates user credentials via email.
    
    Returns:
        Tuple[bool, str, Optional[User]]: (success_status, message, user_object)
    """
    try:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if not user:
            logger.warning(f"⚠️ Login failed — Email not found: {email}")
            return False, "Email not found. Please register first.", None

        logger.info(f"✅ User logged in successfully: {email}")
        return True, "Login successful", user

    except Exception as e:
        logger.error(f"❌ Database error during login for {email}: {str(e)}", exc_info=True)
        raise


# ─── GET ALL USERS ───────────────────────────────────────────────────────────
def get_all_users(db: Session) -> List[User]:
    """
    Fetches all user records from the database.
    """
    try:
        result = db.execute(select(User))
        return list(result.scalars().all())
    except Exception as e:
        logger.error(f"❌ Failed to fetch users: {str(e)}", exc_info=True)
        raise


# ─── DELETE USER ─────────────────────────────────────────────────────────────
def delete_user(db: Session, user_id: int) -> Tuple[bool, str]:
    """
    Deletes a user record by primary key ID.
    
    Returns:
        Tuple[bool, str]: (success_status, message)
    """
    try:
        # Using db.get() is the fastest cache-aware retrieval tool in SQLAlchemy 2.0
        user = db.get(User, user_id)
        if not user:
            logger.warning(f"⚠️ Delete failed — User ID {user_id} not found")
            return False, "User not found"

        db.delete(user)
        db.commit()  # Finalize the removal execution
        
        logger.info(f"✅ User ID {user_id} permanently deleted")
        return True, f"User {user_id} deleted successfully"

    except Exception as e:
        db.rollback() # Rollback truncation if block crashes mid-way
        logger.error(f"❌ Failed to delete user {user_id}: {str(e)}", exc_info=True)
        raise

# database/crud/users.py mein yeh function add karo

def get_user_by_id(db: Session, user_id: int) -> dict:
    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            logger.warning(f"⚠️ User not found: {user_id}")
            return {"success": False, "message": "User not found"}

        return {
            "success": True,
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "is_admin": user.is_admin
        }

    except Exception as e:
        logger.error(f"❌ Fetch failed for user_id {user_id}: {e}")
        raise

def is_admin(db: Session, user_id: int) -> bool:
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        return user.is_admin == 1
    except Exception as e:
        logger.error(f"❌ Admin check failed: {e}")
        raise