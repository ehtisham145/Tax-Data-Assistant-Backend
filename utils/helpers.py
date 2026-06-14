# ─── Dependency: groq_client + retriever ─────────────────────────────────────
import logging
from fastapi import HTTPException,status,Query,Header
from utils.config import ADMIN_API_KEY

logger = logging.getLogger(__name__)

def get_retriever():
    from main import retriever
    return retriever

def get_openai_client():
    from main import openai_client
    return openai_client


# ─── Admin Auth Helper ────────────────────────────────────────────────────────
def verify_admin_key(secret: str = Query(...)) -> None:
    logger.info(f"Received secret: '{secret}'")      # kya aa raha hai
    logger.info(f"Expected secret: '{ADMIN_API_KEY}'") # kya expect hai
    if secret != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )