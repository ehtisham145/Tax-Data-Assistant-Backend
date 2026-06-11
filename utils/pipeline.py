import logging
import asyncio
from utils.scraper import scrap_website
from utils.hasher import hash_content_changed
from utils.ingestor import ingest_text_to_chromadb

# Logger setup
logger = logging.getLogger(__name__)

# Global lock: Yeh ensure karega ke ek waqt me poore server par sirf EK hi pipeline run ho
PIPELINE_LOCK = asyncio.Lock()


async def run_update_pipeline() -> dict:
    """
    Full Production Pipeline:
    1. Acquire Lock (Anti-race condition)
    2. Scrape website with validation
    3. Check if content changed using MD5 Hash
    4. If changed → Atomically ingest into ChromaDB
    5. If not changed → Safe skip
    """
    # 1. Concurrency Safety: Check karein ke kahin pehle se to pipeline nahi chal rahi?
    if PIPELINE_LOCK.locked():
        logger.warning("⚠️ Pipeline is already running! Skipping this trigger to avoid race condition.")
        return {"status": "skipped", "reason": "Pipeline already running"}

    async with PIPELINE_LOCK:
        try:
            # Step 1 — Scrape Data
            logger.info("🌐 Starting website scraping pipeline...")
            scraped_text = await scrap_website()

            # Step 2 — Robust Validation (None check + Length check)
            if not scraped_text or len(scraped_text.strip()) < 500:
                logger.error(
                    f"❌ Scraped text validation failed. Length: {len(scraped_text) if scraped_text else 0} — aborting."
                )
                return {
                    "status": "aborted", 
                    "reason": "Scraped text too short or empty"
                }

            # Step 3 — Check Hash/Content State
            # (Note: hash.py ke andar folder creation automated honi chahiye jo humne pehle fix ki thi)
            if not hash_content_changed(scraped_text):
                return {"status": "skipped", "reason": "Content unchanged"}

            # Step 4 — Ingest into ChromaDB
            logger.info("⚙️ Content change detected! Ingesting fresh data into ChromaDB...")
            success = await ingest_text_to_chromadb(scraped_text)

            if success:
                logger.info("🚀 Pipeline executed successfully — Database updated.")
                return {"status": "updated", "reason": "Fresh data ingested successfully"}
            else:
                logger.error("❌ Pipeline failed during database ingestion step.")
                return {"status": "failed", "reason": "Ingest failed"}

        except Exception as e:
            # exc_info=True se aapko error ka exact line number aur traceback logs me milega
            logger.error(f"❌ Critical Pipeline error: {e}", exc_info=True)
            return {"status": "error", "reason": str(e)}