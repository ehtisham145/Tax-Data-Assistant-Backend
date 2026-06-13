# ─── Dependency: groq_client + retriever ─────────────────────────────────────
import logging
from fastapi import HTTPException
from utils.config import ADMIN_SECRET
from typing import Optional
from database.connections import get_db
import sqlite3


logger = logging.getLogger(__name__)
def get_groq_client():
    """Proper FastAPI dependency — no circular import hack needed."""
    from main import groq_client
    return groq_client

def get_retriever():
    from main import retriever
    return retriever

def get_openai_client():
    from main import openai_client
    return openai_client


# ─── Admin Auth Helper ────────────────────────────────────────────────────────

def verify_admin(secret: str):
    """Check admin secret — raise 403 if wrong."""
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="❌ Not allowed! Admin only.")



