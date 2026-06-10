import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_SECRET=os.getenv("ADMIN_SECRET")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"
JINA_API_KEY = os.getenv("JINA_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "/data/chroma_db")  # ✅ Railway Volume
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "/data/users.db")   # ✅ Railway Volume
MAX_HISTORY = 6
SIMILARITY_TOP_K = 3
REDIS_URL = "redis://localhost:6379"
ALLOWED_ORIGINS = [
    "https://e-numerak.com",
    "http://localhost:3000",
    "https://tax-chatbot-front-end-production.up.railway.app"
]