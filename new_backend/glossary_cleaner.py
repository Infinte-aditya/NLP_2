import json

input_file = "new_glossary.jsonl"   # your input file (line-separated JSON)
output_file = "new_updated_glossary.jsonl" # cleaned output file

cleaned_lines = []

with open(input_file, "r", encoding="utf-8") as infile:
    for line in infile:
        line = line.strip()
        if not line:
            continue
        
        obj = json.loads(line)
        terms = obj.get("term", [])
        
        # keep only if at least one term is non-empty
        if any(term.strip() for term in terms):
            cleaned_lines.append(json.dumps(obj))

with open(output_file, "w", encoding="utf-8") as outfile:
    outfile.write("\n".join(cleaned_lines))

print(f"Cleaned data written to {output_file}")