import logging
import asyncio

from utils.data_pipeline.scraper import run_full_scrape
from utils.data_pipeline.ingestor import run_ingestion
from utils.rag import build_retriever

logger = logging.getLogger(__name__)

# Global lock - ensures only one pipeline run at a time across the server
PIPELINE_LOCK = asyncio.Lock()


async def run_update_pipeline() -> dict:
    """
    Full production pipeline:
    1. Acquire lock (prevent concurrent runs)
    2. Scrape all configured sources -> data/raw/*/...txt
    3. Detect changed/new files via MD5 manifest
    4. Ingest changed files into ChromaDB (delete old chunks + add new)
    5. Rebuild retriever with updated data
    """
    if PIPELINE_LOCK.locked():
        logger.warning("Pipeline is already running - skipping this trigger")
        return {"status": "skipped", "reason": "Pipeline already running"}

    async with PIPELINE_LOCK:
        try:
            # Step 1 - Scrape all sources
            logger.info("Starting scrape...")
            await run_full_scrape()

            # Step 2 + 3 - Detect changes and ingest
            logger.info("Checking for changes and ingesting...")
            summary = await asyncio.to_thread(run_ingestion)

            if summary["files_processed"] == 0:
                logger.info("No changes detected - skipping retriever reload")
                return {"status": "skipped", "reason": "No content changes detected"}

            # Step 4 - Rebuild retriever with fresh data
            logger.info("Reloading retriever with updated data...")
            new_retriever = await asyncio.to_thread(build_retriever)

            import main
            main.retriever = new_retriever

            logger.info("Pipeline completed successfully - database and retriever updated")
            return {
                "status": "updated",
                "files_processed": summary["files_processed"],
                "chunks_added": summary["chunks_added"],
            }

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            return {"status": "error", "reason": str(e)}