"""
Sets up the data/ folder structure for the E-Numerak chatbot's
training/knowledge-base files.

Run this once from your Backend project root:
    python setup_data_structure.py
"""

import json
from pathlib import Path

BASE_DIR = Path("data")

# Folder -> list of files to create inside it
structure = {
    "raw/company_info": [
        "home.txt",
        "services.txt",
        "peppol.txt",
        "fta_compliance.txt",
        "about.txt",
        "contact.txt",
    ],
    "raw/uae_tax_knowledge": [
        "fta_vat_guide.txt",
        "fta_einvoicing_clarifications.txt",
        "mof_einvoicing_overview.txt",
        "pint_ae_technical_guide.txt",
    ],
    "raw/qa_dataset": [
        "faq_pairs.jsonl",
    ],
}

created = []

for folder, files in structure.items():
    dir_path = BASE_DIR / folder
    dir_path.mkdir(parents=True, exist_ok=True)
    for file_name in files:
        file_path = dir_path / file_name
        if not file_path.exists():
            file_path.touch()
            created.append(str(file_path))

# manifest.json -> tracks per-file content hash + last_updated timestamp
manifest_path = BASE_DIR / "manifest.json"
if not manifest_path.exists():
    manifest_path.write_text(json.dumps({}, indent=2), encoding="utf-8")
    created.append(str(manifest_path))

# metadata_schema.json -> defines the metadata fields attached to each
# chunk when it's ingested into ChromaDB
metadata_schema = {
    "source_type": "company_info | uae_tax_knowledge | qa_pair",
    "source_url": "Original URL the content was scraped from, or 'manual' for QA pairs",
    "category": "Topic label, e.g. peppol_onboarding, einvoicing_timeline, vat_registration",
    "last_updated": "YYYY-MM-DD"
}
schema_path = BASE_DIR / "metadata_schema.json"
if not schema_path.exists():
    schema_path.write_text(json.dumps(metadata_schema, indent=2), encoding="utf-8")
    created.append(str(schema_path))

# Print summary
if created:
    print("Created:")
    for path in created:
        print(f"  {path}")
else:
    print("Nothing to create — structure already exists.")

print("\n✅ data/ folder structure is ready!")