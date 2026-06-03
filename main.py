from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from llama_index.core import VectorStoreIndex, Settings
from llama_index.llms.groq import Groq
from llama_index.embeddings.jinaai import JinaEmbedding
from dotenv import load_dotenv
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
import os

load_dotenv()

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","https://e-numerak.com"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# LLM + Embedding setup
llm = Groq(model="llama-3.1-8b-instant", api_key=os.getenv("GROQ_API_KEY"))
embed_model = JinaEmbedding(api_key=os.getenv("JINA_API_KEY"))
Settings.llm = llm
Settings.embed_model = embed_model

# ChromaDB load
chroma_client = chromadb.PersistentClient(path="./chroma_db")
chroma_collection = chroma_client.get_or_create_collection("tax_data")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)
index = VectorStoreIndex.from_vector_store(vector_store)
query_engine = index.as_query_engine(streaming=True)

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def root():
    return {"status": "Tax Chatbot API is running!"}

@app.post("/chat")
async def chat(request: ChatRequest):
    def generate():
        response = query_engine.query(request.message)
        for chunk in response.response_gen:
            yield chunk

    return StreamingResponse(generate(), media_type="text/plain")