import json
import logging
from pathlib import Path

import chromadb
from llama_index.core import Settings, Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding

from utils.config import OPENAI_API_KEY, CHROMA_DB_PATH
from utils.data_pipeline.hasher import scan_for_changes

DATA_DIR = Path("data/raw")

logger = logging.getLogger(__name__)

CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
COLLECTION_NAME = "tax_data"


# ─── Setup ─────────────────────────────────────────────────────────────────
def _get_vector_store() -> ChromaVectorStore:
    Settings.embed_model = OpenAIEmbedding(
        api_key=OPENAI_API_KEY,
        model="text-embedding-3-small",
    )
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
    return ChromaVectorStore(chroma_collection=collection), collection


# ─── Loaders ───────────────────────────────────────────────────────────────
def _load_txt_document(file_info: dict) -> list[Document]:
    """Load a .txt file as a single Document (will be chunked later)."""
    path = Path(file_info["path"])
    text = path.read_text(encoding="utf-8")

    if not text.strip():
        logger.warning(f"Empty file, skipping: {file_info['path']}")
        return []

    return [
        Document(
            text=text,
            metadata={
                "source_path": file_info["path"],
                "source_type": file_info["source_type"],
                "category": file_info["category"],
            },
        )
    ]


def _load_jsonl_qa_document(file_info: dict) -> list[Document]:
    """Load a .jsonl Q&A file - each line becomes its own Document (no further chunking)."""
    path = Path(file_info["path"])
    documents = []

    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                pair = json.loads(line)
                question = pair["question"].strip()
                answer = pair["answer"].strip()
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Skipping malformed line {line_num} in {file_info['path']}: {e}")
                continue

            text = f"Question: {question}\nAnswer: {answer}"
            documents.append(
                Document(
                    text=text,
                    metadata={
                        "source_path": file_info["path"],
                        "source_type": file_info["source_type"],
                        "category": file_info["category"],
                        "qa_line": line_num,
                    },
                )
            )

    return documents


def _load_documents(file_info: dict) -> list[Document]:
    path = Path(file_info["path"])
    if path.suffix == ".jsonl":
        return _load_jsonl_qa_document(file_info)
    elif path.suffix == ".txt":
        return _load_txt_document(file_info)
    else:
        logger.warning(f"Unsupported file type, skipping: {file_info['path']}")
        return []


# ─── Deletion ──────────────────────────────────────────────────────────────
def _delete_existing_chunks(collection, source_path: str) -> None:
    """Remove all existing chunks for a given source file before re-ingesting."""
    try:
        existing = collection.get(where={"source_path": source_path})
        ids = existing.get("ids", [])
        if ids:
            collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} existing chunk(s) for {source_path}")
    except Exception as e:
        logger.error(f"Failed to delete existing chunks for {source_path}: {e}", exc_info=True)
        raise


# ─── Ingestion ─────────────────────────────────────────────────────────────
def ingest_file(file_info: dict, vector_store: ChromaVectorStore, collection, splitter: SentenceSplitter) -> int:
    """
    Ingest a single changed/new file: delete its old chunks, split into new
    chunks, embed, and add to ChromaDB. Returns number of chunks added.
    """
    documents = _load_documents(file_info)
    if not documents:
        return 0

    _delete_existing_chunks(collection, file_info["path"])

    # .jsonl Q&A docs are already small - don't re-split them.
    # .txt docs get split into chunks via SentenceSplitter.
    if Path(file_info["path"]).suffix == ".jsonl":
        nodes = [doc.as_related_node_info() for doc in documents]
        # as_related_node_info doesn't give usable nodes - build nodes directly
        from llama_index.core.schema import TextNode
        nodes = [
            TextNode(text=doc.text, metadata=doc.metadata)
            for doc in documents
        ]
    else:
        nodes = splitter.get_nodes_from_documents(documents)

    if not nodes:
        logger.warning(f"No nodes produced for {file_info['path']}")
        return 0

    # Embed and add to vector store
    embed_model = Settings.embed_model
    for node in nodes:
        node.embedding = embed_model.get_text_embedding(node.get_content())

    vector_store.add(nodes)
    logger.info(f"Ingested {len(nodes)} chunk(s) from {file_info['path']}")
    return len(nodes)


def run_ingestion() -> dict:
    """
    Main entry point: scan for changed files, ingest each into ChromaDB.
    Returns a summary dict with counts.
    """
    changed_files = scan_for_changes()

    if not changed_files:
        logger.info("No files to ingest - ChromaDB is up to date")
        return {"files_processed": 0, "chunks_added": 0}

    vector_store, collection = _get_vector_store()
    splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    total_chunks = 0
    files_processed = 0

    for file_info in changed_files:
        try:
            chunks_added = ingest_file(file_info, vector_store, collection, splitter)
            total_chunks += chunks_added
            files_processed += 1
        except Exception as e:
            logger.error(f"Failed to ingest {file_info['path']}: {e}", exc_info=True)
            # Continue with other files rather than aborting the whole run
            continue

    logger.info(f"Ingestion complete: {files_processed} file(s), {total_chunks} chunk(s) added")
    return {"files_processed": files_processed, "chunks_added": total_chunks}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    summary = run_ingestion()
    print(f"\nDone: {summary['files_processed']} file(s), {summary['chunks_added']} chunk(s) added")