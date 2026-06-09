from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.llms.groq import Groq
from llama_index.embeddings.jinaai import JinaEmbedding
from dotenv import load_dotenv
import os
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext

load_dotenv()

llm = Groq(model="llama-3.1-8b-instant", api_key=os.getenv("GROQ_API_KEY"))
embed_model = JinaEmbedding(api_key=os.getenv("JINA_API_KEY"))

Settings.llm = llm
Settings.embed_model = embed_model

chroma_client = chromadb.PersistentClient(path="./chroma_db")
chroma_collection = chroma_client.get_or_create_collection("tax_data")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

documents = SimpleDirectoryReader(input_files=["portal_data.txt"]).load_data()
index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)

print("✅ Data ingested successfully!")