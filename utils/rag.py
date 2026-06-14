import os
import logging

from llama_index.core import (
    VectorStoreIndex,
    Settings,
    SimpleDirectoryReader,
    StorageContext,
)

from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

from utils.config import OPENAI_API_KEY, CHROMA_DB_PATH

logger = logging.getLogger(__name__)


def build_retriever(similarity_top_k: int = 3):
    """
    Build (or load) the vector index and return a retriever.
    Loads existing ChromaDB data if present, otherwise ingests from source data.
    """
    embed_model = OpenAIEmbedding(
        api_key=OPENAI_API_KEY,
        model="text-embedding-3-small",  # cheaper, 1536 dims; use "text-embedding-3-large" for higher quality
    )
    Settings.embed_model = embed_model
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    chroma_collection = chroma_client.get_or_create_collection("tax_data")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    if os.path.exists(CHROMA_DB_PATH) and len(chroma_collection.get()["ids"]) > 0:
        index = VectorStoreIndex.from_vector_store(vector_store)
        logger.info("Loaded existing ChromaDB data")
    else:
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        documents = SimpleDirectoryReader(input_files=["training_data/portal_data.txt"]).load_data()
        index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
        logger.info("Ingested fresh data into ChromaDB")

    return index.as_retriever(similarity_top_k=similarity_top_k)