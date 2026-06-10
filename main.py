import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from utils.config import (
    GROQ_API_KEY, JINA_API_KEY,
    CHROMA_DB_PATH, ALLOWED_ORIGINS, OPENAI_API_KEY)
from database.init_db import init_db

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ─── Global Clients (module-level, initialized in lifespan) ──────────────────

groq_client = None
openai_client = None
retriever = None


# ─── Lifespan — Startup & Shutdown ───────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """All startup logic here — clean, structured, error-friendly."""
    global groq_client, openai_client, retriever

    # 1. Database
    try:
        init_db()
    except Exception as e:
        logger.critical(f"❌ Database init failed: {e}")
        raise

    # # 2. Groq Client
    # try:
    #     from groq import Groq as GroqClient
    #     groq_client = GroqClient(api_key=GROQ_API_KEY)
    #     logger.info("✅ Groq client initialized!")
    # except Exception as e:
    #     logger.critical(f"❌ Groq init failed: {e}")
    #     raise

    # 3. OpenAI Client
    try:
        from openai import AsyncOpenAI
        openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        logger.info("OpenAI client initialized!")
    except Exception as e:
        logger.critical(f"OpenAI init failed: {e}")
        raise

    # 4. Embeddings + ChromaDB + Retriever
    try:
        from llama_index.core import VectorStoreIndex, Settings, SimpleDirectoryReader
        from llama_index.embeddings.jinaai import JinaEmbedding
        from llama_index.vector_stores.chroma import ChromaVectorStore
        from llama_index.core import StorageContext
        import chromadb

        embed_model = JinaEmbedding(api_key=JINA_API_KEY)
        Settings.embed_model = embed_model

        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        chroma_collection = chroma_client.get_or_create_collection("tax_data")
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        if os.path.exists(CHROMA_DB_PATH) and len(chroma_collection.get()["ids"]) > 0:
            index = VectorStoreIndex.from_vector_store(vector_store)
            logger.info("✅ Existing ChromaDB data loaded!")
        else:
            documents = SimpleDirectoryReader(input_files=["/data/portal_data.txt"]).load_data()
            index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
            logger.info("✅ Fresh data ingested into ChromaDB!")

        retriever = index.as_retriever(similarity_top_k=3)
        logger.info("✅ Retriever ready!")

    except Exception as e:
        logger.critical(f"❌ ChromaDB/Retriever init failed: {e}")
        raise

    logger.info("🚀 E-Numerak API startup complete!")
    yield  # ← Server yahan chalta hai

    # Shutdown
    logger.info("🛑 E-Numerak API shutting down...")


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="E-Numerak Tax Chatbot API",
    description="UAE Tax Assistant powered by E-Numerak",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── Rate Limiter ─────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ─── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# ─── Routers ──────────────────────────────────────────────────────────────────

from routes.auth import router as auth_router
from routes.chat import router as chat_router

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(chat_router, prefix="/chat", tags=["Chat"])

# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {"status": "E-Numerak Tax Chatbot API is running!"}


@app.get("/health", tags=["Health"])
def health_check():
    """Deployment health check — Railway/Render is use karta hai."""
    return {
        "status": "healthy",
        "groq": groq_client is not None,
        "openai": openai_client is not None,
        "retriever": retriever is not None,
    }


@app.get("/test-openai", tags=["Health"])
async def test_openai():
    """Quick test to verify OpenAI GPT-4o-mini is working."""
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say hello in one sentence."}],
            max_tokens=50,
        )
        return {
            "status": "success",
            "model": response.model,
            "reply": response.choices[0].message.content,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}