# run_once_cleanup.py  — run from project root then delete
import json, re

with open("english_tamil_hindi_glossary.json", "r", encoding="utf-8") as f:
    g = json.load(f)

# Remove entries where both hi and ta equal the English key (untransliterated)
bad = [k for k, v in g.items() 
       if isinstance(v, dict) 
       and v.get("hi", "") == k 
       and v.get("ta", "") == k]

print(f"Removing {len(bad)} bad entries: {bad}")
for k in bad:
    del g[k]

with open("english_tamil_hindi_glossary.json", "w", encoding="utf-8") as f:
    json.dump(g, f, ensure_ascii=False, indent=2)

print("Done.")