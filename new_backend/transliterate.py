"""
add_malay_protection.py
Automatically adds "ms": "Original English Term" to every entry in updated_glossary.json
This makes the glossary act as a "Protect List" for Malay translations.
"""

import json
from pathlib import Path
import shutil

# ========================= CONFIG =========================
GLOSSARY_PATH = Path("upg.json")   # Change only if your file is elsewhere
BACKUP = True
# ========================================================

def add_malay_keys():
    if not GLOSSARY_PATH.exists():
        print(f"❌ Error: File not found → {GLOSSARY_PATH}")
        return

    # Load current glossary
    with open(GLOSSARY_PATH, "r", encoding="utf-8") as f:
        glossary = json.load(f)

    original_count = len(glossary)
    updated_count = 0

    print(f"🔄 Processing {original_count} terms...")

    for term, translations in glossary.items():
        # Add or update "ms" key with the exact English term
        translations["ms"] = term
        updated_count += 1

    # Create backup before saving
    if BACKUP:
        backup_path = GLOSSARY_PATH.with_name(GLOSSARY_PATH.stem + "_backup_before_ms.json")
        shutil.copy2(GLOSSARY_PATH, backup_path)
        print(f"✅ Backup created: {backup_path.name}")

    # Save updated glossary
    with open(GLOSSARY_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(glossary, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 SUCCESS!")
    print(f"   • Processed terms          : {original_count}")
    print(f"   • Added/Updated 'ms' keys  : {updated_count}")
    print(f"   • Malay now protects English terms (no translation)")
    print(f"\n📁 Updated file: {GLOSSARY_PATH.resolve()}")

if __name__ == "__main__":
    print("=== Add Malay Protection to Glossary ===\n")
    add_malay_keys()