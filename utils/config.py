import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
JINA_API_KEY = os.getenv("JINA_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"
CHROMA_DB_PATH = "./chroma_db"
SQLITE_DB_PATH = "users.db"
MAX_HISTORY = 6
SIMILARITY_TOP_K = 3
REDIS_URL = "redis://localhost:6379"
ALLOWED_ORIGINS = ["https://e-numerak.com","http://localhost:3000","https://tax-chatbot-front-end-production.up.railway.app"]