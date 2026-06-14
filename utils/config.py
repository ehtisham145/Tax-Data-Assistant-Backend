import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_API_KEY=os.getenv("ADMIN_API_KEY")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


OPENAI_MODEL = "gpt-4o-mini"

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH")
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH")

MAX_HISTORY = 6
SIMILARITY_TOP_K = 3

DOCS_URL = os.getenv("DOCS_URL")

ALLOWED_ORIGINS = [
    "https://e-numerak.com",
    "http://localhost:3000",
    "https://tax-chatbot-front-end-production.up.railway.app"
]

MANIFEST_FILE_PATH = os.getenv("MANIFEST_FILE_PATH")
print(SQLITE_DB_PATH)