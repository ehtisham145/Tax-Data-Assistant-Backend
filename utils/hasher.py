"""First run:
No hash file exists → get_saved_hash() returns ""
Scrape runs → hash generated → saved to /data/content_hash.txt ✅

Second run:
/data/content_hash.txt exists → old hash loaded
New hash compared with old hash
Same? → Skip    Different? → Update ✅"""

import hashlib
import os
from pathlib import Path
import logging

logger=logging.getLogger(__name__)

# Store hash file in Railway Volume so it persists between deploys
HASH_FILE_PATH = os.getenv("HASH_FILE_PATH", "/data/content_hash.txt")

def generate_hash(text:str)->str:
    """Generate MD5 hash of the given text."""
    if not text:
        return ""
    """MD5 Hashing Algorithm Accepts Bytes thats why we convert our text into bytes first using encode algoruthm"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def save_hash(hash_value: str) -> None:
    """Save the new hash to file safely by creating directories if missing."""
    try:
        # 1. Ensure the parent directory exists (e.g., /data/ folder)
        file_path = Path(HASH_FILE_PATH)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 2. Save the hash safely using a temporary file (Atomic Write Pattern)
        temp_file = f"{HASH_FILE_PATH}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(hash_value)
        
        # Rename temp file to actual file (Atomic operation in Linux)
        os.replace(temp_file, HASH_FILE_PATH)
        logger.info("💾 New hash saved successfully.")
        
    except Exception as e:
        logger.error(f"💥 Failed to save hash to {HASH_FILE_PATH}: {e}")
        # Production alert: In real production, you might want to raise this 
        # or handle it depending on if crashing is acceptable.


def get_saved_hash()->str:
    """Read the previously saved hash from file safely."""
    try:
        with open(HASH_FILE_PATH,"r",encoding="utf-8") as f:
            return f.read().strip()
    
    except FileNotFoundError:
        logger.info("📄 No previous hash found — first time running.")
        return ""
    
    except Exception as e:
        logger.error(f"❌ Error reading hash file: {e}")
        return ""
    

def hash_content_changed(new_text:str)->bool:
    """This Function will compare new content with hash"""
    if not new_text:
        logger.warning("⚠️ Received empty text to compare. Skipping.")
        return False
    
    new_hash=generate_hash(new_text)
    old_hash=get_saved_hash()

    if new_hash == old_hash:
        logger.info("✅ Content unchanged — skipping update.")
        return False
    
    logger.info("🔄 Content changed — update needed.")
    save_hash(new_hash)
    return True

# ─── Runner / Main Block ─────────────────────────────────────────────────────

# if __name__ == "__main__":
#     # Setup simple logging console par dekhne ke liye
#     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
#     print("🚀 Starting Hash Module Test...\n")
    
#     # Test Content
#     sample_scraped_text = "This is the clean text scraped from e-numerak.com website."
    
#     # RUN 1: Pehli baar chalana (Naya data save hona chahiye)
#     print("--- Test Run 1: Checking fresh content ---")
#     is_changed_1 = hash_content_changed(sample_scraped_text)
#     print(f"Result 1: Should we update? -> {is_changed_1}\n")
    
#     # RUN 2: Doosri baar chalana same data ke sath (Skip hona chahiye)
#     print("--- Test Run 2: Checking same content again ---")
#     is_changed_2 = hash_content_changed(sample_scraped_text)
#     print(f"Result 2: Should we update? -> {is_changed_2}\n")
    
#     # RUN 3: Cheating Test (Data thoda badal kar dekhna)
#     print("--- Test Run 3: Checking modified content ---")
#     modified_text = sample_scraped_text + " Add some new updates here."
#     is_changed_3 = hash_content_changed(modified_text)
#     print(f"Result 3: Should we update? -> {is_changed_3}\n")