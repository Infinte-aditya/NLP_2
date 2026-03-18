import json
from backend.pipeline.postprocessing import get_active_fallback
import os

GLOSSARY_PATH = "english_tamil_hindi_glossary.json"

if not os.path.exists(GLOSSARY_PATH):
    print("Glossary not found.")
    exit(1)

with open(GLOSSARY_PATH, "r", encoding="utf-8") as f:
    glossary = json.load(f)

tamil_fallback = get_active_fallback("Tamil")
hindi_fallback = get_active_fallback("Hindi")

updates_tam = 0
updates_hin = 0

for eng, tam in tamil_fallback.items():
    if eng not in glossary:
        glossary[eng] = {}
    if "ta" not in glossary[eng] or not glossary[eng]["ta"]:
        glossary[eng]["ta"] = tam
        updates_tam += 1

for eng, hi in hindi_fallback.items():
    if eng not in glossary:
        glossary[eng] = {}
    if "hi" not in glossary[eng] or not glossary[eng]["hi"]:
        glossary[eng]["hi"] = hi
        updates_hin += 1

with open(GLOSSARY_PATH, "w", encoding="utf-8") as f:
    json.dump(glossary, f, ensure_ascii=False, indent=2)

print(f"Glossary updated: added {updates_tam} Tamil terms, {updates_hin} Hindi terms.")
