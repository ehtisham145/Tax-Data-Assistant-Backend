import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from llama_index.core import VectorStoreIndex, Settings
from llama_index.embeddings.jinaai import JinaEmbedding
from groq import Groq as GroqClient
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
from config import (
    GROQ_API_KEY, JINA_API_KEY,
    CHROMA_DB_PATH, ALLOWED_ORIGINS
)
from database import init_db
from routes.auth import router as auth_router
from routes.chat import router as chat_router
import os

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="E-Numerak Tax Chatbot API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://e-numerak.com","http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Initialize Groq client
groq_client = GroqClient(api_key=GROQ_API_KEY)

# Initialize Jina embeddings
embed_model = JinaEmbedding(api_key=JINA_API_KEY)
Settings.embed_model = embed_model

# ChromaDB setup
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
chroma_collection = chroma_client.get_or_create_collection("tax_data")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Load or ingest documents
if os.path.exists(CHROMA_DB_PATH) and len(chroma_collection.get()["ids"]) > 0:
    index = VectorStoreIndex.from_vector_store(vector_store)
    logger.info("✅ Existing ChromaDB data loaded!")
else:
    from llama_index.core import SimpleDirectoryReader
    documents = SimpleDirectoryReader(input_files=["sample_data.txt"]).load_data()
    index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
    logger.info("✅ Fresh data ingested into ChromaDB!")

# Retriever — top 3 relevant chunks
retriever = index.as_retriever(similarity_top_k=3)

# Initialize SQLite DB
init_db()

# Register routers
app.include_router(auth_router)
app.include_router(chat_router)

@app.get("/")
def root():
    return {"status": "E-Numerak Tax Chatbot API is running!"}