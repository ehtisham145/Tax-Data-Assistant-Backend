import logging
import os
import chromadb
from llama_index.core import VectorStoreIndex, Document, Settings, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.jinaai import JinaEmbedding
from pathlib import Path
import asyncio
from dotenv import load_dotenv
load_dotenv()

# Setup Logger
logger = logging.getLogger(__name__)

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "/data/chroma_db")
COLLECTION_NAME = "tax_data"

def setup_settings()->None:
    """Initialized LLMs and Embedding Models Globally for llama index"""
    openai_key = os.getenv("OPENAI_API_KEY")
    jina_key = os.getenv("JINA_API_KEY")

    #Check API Keys are Configured
    if not openai_key or not jina_key:
        logger.critical("❌ Missing API Keys! Ensure OPENAI_API_KEY and JINA_API_KEY are set.")
        raise ValueError("Missing required API keys in environment variables.")
    
    # Set your LLM
    llm = OpenAI(
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key = openai_key
    )
    # Embedding Model
    embed_model = JinaEmbedding(api_key=jina_key)

    Settings.llm = llm
    Settings.embed_model = embed_model
    logger.info("✅ LlamaIndex Global Settings initialized successfully.")


setup_settings()

async def ingest_text_to_chromadb(text: str) -> bool:
    """Clear old ChromaDB data and ingest fresh scraped text safely."""
    # Edge case check: Agar input text khali hai to aage badhne ki zaroorat nahi
    if not text or not text.strip():
        logger.warning("⚠️ Received empty text for ingestion. Skipping.")
        return False

    try:
        # 1. Ensure the DB folder exists (Railway Volume Safety)
        Path(CHROMA_DB_PATH).mkdir(parents=True, exist_ok=True)

        # 2. Connect to ChromaDB Client
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

        # 3. Safe Collection Reset (Fixes the first-time run crash bug)
        try:
            chroma_client.delete_collection(COLLECTION_NAME)
            logger.info(f"🗑️ Existing collection '{COLLECTION_NAME}' deleted.")
        except (ValueError, KeyError, Exception):
            # Agar collection pehle se nahi bani hui to delete_collection error dega
            # Hum use catch kar ke ignore kar denge kyunki masla nahi hai
            logger.info(f"ℹ️ Collection '{COLLECTION_NAME}' did not exist. Creating a fresh one.")

        # Recreate a fresh collection
        chroma_collection = chroma_client.get_or_create_collection(COLLECTION_NAME)

        # 4. Setup vector store context
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        # 5. Convert text to LlamaIndex Document
        document = Document(text=text)

        # 6. Ingest data asynchronously into ChromaDB
        # Production tuning: 'show_progress=False' in logs to keep production logs clean
        VectorStoreIndex.from_documents(
            [document],
            storage_context=storage_context,
            show_progress=False,  
        )

        logger.info("✅ Fresh data vectorised and ingested into ChromaDB successfully!")
        return True

        # ChromaDB connection automatically cleans up or persists in PersistentClient

    except Exception as e:
        logger.error(f"❌ Ingest failed due to unexpected error: {e}", exc_info=True)
        return False

def query_chromadb(text:str)->str:
    """Helper function to test and query your ChromaDB index."""
    try:
        chroma_client=chromadb.PersistentClient(path=CHROMA_DB_PATH)
        chroma_collection=chroma_client.get_collection(COLLECTION_NAME)
        if not chroma_collection:
            logger.warning("No Collection Found")
        
        vector_store=ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        # Load index from the existing vector store
        index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)

        query_engine = index.as_query_engine()
        response = query_engine.query(text)
        return str(response)
    except Exception as e:
        logger.error(f"❌ Query failed: {e}")
        return f"Error querying data: {e}"
    

# async def main():
#     print("🚀 --- STARTING CHROMADB INGESTION & QUERY TEST ---")
    
#     # Check if API keys exist
#     if not os.getenv("OPENAI_API_KEY") or not os.getenv("JINA_API_KEY"):
#         print("❌ Error: Please set OPENAI_API_KEY and JINA_API_KEY in your environment first.")
#         return

#     # Website ka fake/mock data test karne ke liye
#     mock_website_data = """
#     Welcome to E-Numerak Corporate Portal. 
#     We specialize in Corporate Tax registration, FTA compliance, and automated Peppol e-invoicing.
#     Our head office is located in Dubai, UAE, and you can contact our helpdesk at info@e-numerak.com.
#     We help businesses digitize their accounting processes securely.
#     """

#     print("\n📥 Step 1: Ingesting mock web text into ChromaDB...")
#     success = await ingest_text_to_chromadb(mock_website_data)
    
#     if success:
#         print("✅ Ingestion Completed!")
#         print(f"📁 Checking if ChromaDB folder exists at: {CHROMA_DB_PATH} -> {os.path.exists(CHROMA_DB_PATH)}")
        
#         # 2. Query Test (AI se sawal poochna)
#         print("\n🔍 Step 2: Testing Chat/Query Engine on ChromaDB...")
#         question = "Where is E-Numerak head office located and what is their email?"
#         print(f"Question: '{question}'")
        
#         print("AI is thinking...")
#         answer = query_chromadb(question)
        
#         print("\n🤖 AI Response:")
#         print("=" * 60)
#         print(answer)
#         print("=" * 60)
        
#     else:
#         print("❌ Ingestion Failed. Check logs above.")

# if __name__ == "__main__":
#     asyncio.run(main())