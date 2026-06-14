"""
Per-file version of hashing.py — instead of one hash for a single combined
blob, this maintains a JSON manifest with one hash per file under data/raw/.

First run:
    manifest file doesn't exist -> load_manifest() returns {}
    every file is "new" -> all get added to manifest -> saved

Second run:
    manifest exists -> old hashes loaded
    each file's new hash compared with its old hash
    Same? -> Skip    Different/new? -> mark as changed + update manifest
"""

import hashlib
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from utils.config import MANIFEST_FILE_PATH

logger = logging.getLogger(__name__)


DATA_DIR = Path("data/raw")

# Maps the top-level folder name under data/raw/ -> source_type metadata
# value that will be stored alongside each chunk in ChromaDB.
SOURCE_TYPE_MAP = {
    "company_info": "company_info",
    "uae_tax_knowledge": "uae_tax_knowledge",
    "qa_dataset": "qa_pair",
}

VALID_EXTENSIONS = {".txt", ".jsonl"}


def generate_hash(text: str) -> str:
    """Generate MD5 hash of the given text."""
    if not text:
        return ""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def load_manifest() -> dict:
    """Read the previously saved manifest from file safely."""
    try:
        with open(MANIFEST_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    except FileNotFoundError:
        logger.info("📄 No previous manifest found — first time running.")
        return {}

    except Exception as e:
        logger.error(f"❌ Error reading manifest file: {e}")
        return {}


def save_manifest(manifest: dict) -> None:
    """Save the manifest to file safely (atomic write, like save_hash)."""
    try:
        file_path = Path(MANIFEST_FILE_PATH)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        temp_file = f"{MANIFEST_FILE_PATH}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        os.replace(temp_file, MANIFEST_FILE_PATH)
        logger.info("💾 Manifest saved successfully.")

    except Exception as e:
        logger.error(f"💥 Failed to save manifest to {MANIFEST_FILE_PATH}: {e}")


def scan_for_changes() -> list[dict]:
    """
    Scan data/raw/<company_info|uae_tax_knowledge|qa_dataset>/ for new or
    changed files, comparing each file's MD5 hash against the manifest.

    Returns a list of dicts, one per changed/new file:
        {
            "path": "data/raw/company_info/home.txt",
            "source_type": "company_info",
            "category": "home",
            "hash": "..."
        }

    The manifest is updated and saved automatically. Files that have been
    deleted since the last run are also removed from the manifest.
    """
    manifest = load_manifest()
    changed_files = []
    seen_paths = set()

    for source_folder, source_type in SOURCE_TYPE_MAP.items():
        folder_path = DATA_DIR / source_folder
        if not folder_path.exists():
            logger.warning(f"⚠️ Folder not found, skipping: {folder_path}")
            continue

        for file_path in sorted(folder_path.iterdir()):
            if file_path.suffix not in VALID_EXTENSIONS:
                continue

            rel_path = file_path.as_posix()
            seen_paths.add(rel_path)

            content = file_path.read_text(encoding="utf-8")
            new_hash = generate_hash(content)
            old_entry = manifest.get(rel_path)

            if old_entry is None or old_entry.get("hash") != new_hash:
                category = file_path.stem  # filename without extension

                manifest[rel_path] = {
                    "hash": new_hash,
                    "source_type": source_type,
                    "category": category,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }

                changed_files.append({
                    "path": rel_path,
                    "source_type": source_type,
                    "category": category,
                    "hash": new_hash,
                })
                logger.info(f"🔄 Changed/new: {rel_path}")
            else:
                logger.info(f"✅ Unchanged: {rel_path}")

    # Remove manifest entries for files that no longer exist on disk
    removed = [p for p in manifest if p not in seen_paths]
    for p in removed:
        logger.info(f"🗑️ Removing deleted file from manifest: {p}")
        del manifest[p]

    if changed_files or removed:
        save_manifest(manifest)
    else:
        logger.info("✅ No changes detected — nothing to update.")

    return changed_files


# ─── Runner / Main Block ─────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    print("🚀 Scanning data/raw/ for changes...\n")
    changes = scan_for_changes()

    print(f"\n📊 {len(changes)} file(s) need (re)ingestion:")
    for c in changes:
        print(f"  - {c['path']} ({c['source_type']} / {c['category']})")