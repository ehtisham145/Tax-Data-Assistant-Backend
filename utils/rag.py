import os
import json
import logging

from llama_index.core import VectorStoreIndex, Settings, StorageContext, Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

from utils.config import OPENAI_API_KEY, CHROMA_DB_PATH

logger = logging.getLogger(__name__)

DATA_DIR = os.environ.get("TRAINING_DATA_PATH", "data/raw")


def load_all_documents(data_dir: str) -> list:
    """
    Recursively load all files — JSONL files ko properly parse karo,
    baaki files ko plain text ki tarah.
    """
    docs = []

    for root, _, files in os.walk(data_dir):
        for filename in files:
            filepath = os.path.join(root, filename)

            # JSONL files — Q+A+paraphrases combine karke ek document banao
            if filename.endswith(".jsonl"):
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            
                            # Question + paraphrases + answer — sab ek saath
                            question = obj.get("question", "")
                            answer = obj.get("answer", "")
                            paraphrases = obj.get("paraphrases", [])
                            category = obj.get("category", "")
                            
                            # Ek rich text banao taake embedding accurate ho
                            text = f"Question: {question}\n"
                            
                            if paraphrases:
                                text += f"Also asked as: {' | '.join(paraphrases)}\n"
                            
                            if category:
                                text += f"Category: {category}\n"
                            
                            text += f"Answer: {answer}"
                            
                            docs.append(Document(
                                text=text,
                                metadata={
                                    "id": obj.get("id", ""),
                                    "source": obj.get("source", filename),
                                    "filename": filename
                                }
                            ))
                        except json.JSONDecodeError:
                            logger.warning(f"Skipping invalid JSON line in {filename}")

            # Plain text / txt files
            elif filename.endswith(".txt"):
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        docs.append(Document(
                            text=content,
                            metadata={"source": filename, "filename": filename}
                        ))

    logger.info(f"Total documents loaded: {len(docs)}")
    return docs


def build_retriever(similarity_top_k: int = 8):  # 3 se 8 kar diya
    embed_model = OpenAIEmbedding(
        api_key=OPENAI_API_KEY,
        model="text-embedding-3-small",
    )
    Settings.embed_model = embed_model
    
    # Chunk size bada — taake Q+A split na ho
    Settings.text_splitter = SentenceSplitter(
        chunk_size=512,
        chunk_overlap=50
    )

    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    chroma_collection = chroma_client.get_or_create_collection("tax_data")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    if os.path.exists(CHROMA_DB_PATH) and len(chroma_collection.get()["ids"]) > 0:
        index = VectorStoreIndex.from_vector_store(vector_store)
        logger.info("Loaded existing ChromaDB data")
    else:
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        documents = load_all_documents(DATA_DIR)
        
        if not documents:
            raise ValueError(f"No documents found in {DATA_DIR}")
        
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context
        )
        logger.info(f"Ingested {len(documents)} documents into ChromaDB")

    return index.as_retriever(similarity_top_k=similarity_top_k)