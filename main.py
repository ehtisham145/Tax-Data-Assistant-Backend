import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address



from utils.config import (
    DOCS_URL,
    ALLOWED_ORIGINS,
    OPENAI_API_KEY,
)
from database_setup.init_db import init_db
from utils.rag import build_retriever  # shared retriever-building logic
from migrations.migrate import migrate

from routes.auth import router as auth_router
from routes.chat import router as chat_router
from routes.admin import router as admin_router
from routes.feedback import router as feedback_router

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Global Clients ───────────────────────────────────────────────────────────
openai_client = None
retriever = None


# ─── Lifespan — Startup & Shutdown ───────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global openai_client, retriever

    # 1. Ensure tables exist (idempotent safety net alongside migrations)
    try:
        migrate()
        logger.info("Migrations applied successfully")
    except Exception as e:
        logger.critical(f"Migration failed: {e}", exc_info=True)
        raise

    # 2. Ensure tables exist (idempotent safety net)
    try:
        init_db()
    except Exception as e:
        logger.critical(f"Database init failed: {e}", exc_info=True)
        raise

    # 3. OpenAI client
    try:
        from openai import AsyncOpenAI
        openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        logger.info("OpenAI client initialized")
    except Exception as e:
        logger.critical(f"OpenAI init failed: {e}", exc_info=True)
        raise

    # 4. Retriever (embeddings + ChromaDB)
    try:
        retriever = build_retriever()
        logger.info("Retriever ready")
    except Exception as e:
        logger.critical(f"Retriever init failed: {e}", exc_info=True)
        raise

    logger.info("E-Numerak API startup complete")
    yield

    logger.info("E-Numerak API shutting down")


# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="E-Numerak Tax Chatbot API",
    description="UAE Tax Assistant powered by E-Numerak",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=f"/docs/{DOCS_URL}" if DOCS_URL else None,
    redoc_url=None,
    openapi_url=f"/openapi/{DOCS_URL}.json" if DOCS_URL else None,
)

# ─── Rate Limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    allow_credentials=True,
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(chat_router, prefix="/chat", tags=["Chat"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(feedback_router,prefix="/feedback",tags=["Feedback"])

# ─── Health Endpoints ─────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {"status": "E-Numerak Tax Chatbot API is running"}


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "openai": openai_client is not None,
        "retriever": retriever is not None,
    }