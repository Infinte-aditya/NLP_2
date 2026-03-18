"""
Diagnostic script - writes output to file to handle Tamil encoding.
"""
import re, sys, io
from bs4 import BeautifulSoup
import difflib

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def strip_to_indic_only(text: str) -> str:
    text = text.replace("@@", "")
    text = re.sub(r'\([A-Za-z][A-Za-z\s/&\-,\.]*\)', '', text)
    text = re.sub(r'[A-Za-z]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\(\s*\)', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

TEXT_TAGS = ['ptxt', 'title', 'ftnote', 'text', 'entry', 'para']

def extract_text_nodes(soup):
    nodes = []
    for tag in soup.find_all(TEXT_TAGS):
        raw = tag.get_text(separator=" ").strip()
        if raw:
            clean = strip_to_indic_only(raw)
            nodes.append({"raw": raw, "clean": clean, "tag": tag.name})
    return nodes

ref_path = "tamil.xml"
trans_path = "translated-tamil.xml"

with open(ref_path, "r", encoding="utf-8") as f:
    ref_soup = BeautifulSoup(f.read(), "xml")
with open(trans_path, "r", encoding="utf-8") as f:
    trans_soup = BeautifulSoup(f.read(), "xml")

ref_nodes = extract_text_nodes(ref_soup)
trans_nodes = extract_text_nodes(trans_soup)

out = []
out.append(f"Reference nodes: {len(ref_nodes)}")
out.append(f"Translated nodes: {len(trans_nodes)}")
out.append(f"Difference: {abs(len(ref_nodes) - len(trans_nodes))}")

# Count skipped nodes
ref_skipped = sum(1 for n in ref_nodes if len(n['clean']) < 2)
trans_skipped = sum(1 for n in trans_nodes if len(n['clean']) < 2)
out.append(f"\nRef nodes skipped (clean < 2 chars): {ref_skipped}/{len(ref_nodes)} = {ref_skipped/max(len(ref_nodes),1)*100:.1f}%")
out.append(f"Trans nodes skipped (clean < 2 chars): {trans_skipped}/{len(trans_nodes)} = {trans_skipped/max(len(trans_nodes),1)*100:.1f}%")

# Show what stripping does to first few ref nodes
out.append("\n" + "="*80)
out.append("WHAT strip_to_indic_only DOES TO REF TEXT (first 8 nodes):")
out.append("="*80)
for i in range(min(8, len(ref_nodes))):
    node = ref_nodes[i]
    out.append(f"\n--- Ref Node {i} ({node['tag']}) ---")
    out.append(f"  RAW:   {node['raw'][:250]}")
    out.append(f"  CLEAN: {node['clean'][:250]}")
    if len(node['clean']) < 2:
        out.append(f"  >>> WOULD BE SKIPPED")

# Same for trans
out.append("\n" + "="*80)
out.append("WHAT strip_to_indic_only DOES TO TRANS TEXT (first 8 nodes):")
out.append("="*80)
for i in range(min(8, len(trans_nodes))):
    node = trans_nodes[i]
    out.append(f"\n--- Trans Node {i} ({node['tag']}) ---")
    out.append(f"  RAW:   {node['raw'][:250]}")
    out.append(f"  CLEAN: {node['clean'][:250]}")
    if len(node['clean']) < 2:
        out.append(f"  >>> WOULD BE SKIPPED")

# Alignment analysis
ref_tags = [n["tag"] for n in ref_nodes]
trans_tags = [n["tag"] for n in trans_nodes]
sm = difflib.SequenceMatcher(None, ref_tags, trans_tags)

aligned = 0
unaligned_ref = 0
unaligned_trans = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag in ('equal', 'replace'):
        aligned += min(i2-i1, j2-j1)
    if tag == 'delete':
        unaligned_ref += (i2 - i1)
    if tag == 'insert':
        unaligned_trans += (j2 - j1)

out.append(f"\nAlignment Analysis:")
out.append(f"  Aligned pairs: {aligned}")
out.append(f"  Unaligned ref nodes: {unaligned_ref}")
out.append(f"  Unaligned trans nodes: {unaligned_trans}")

# Sample comparisons from around the worst segments
out.append("\n" + "="*80)
out.append("SAMPLE PAIRS BEING COMPARED (first 5 actual comparisons):")
out.append("="*80)
count = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag in ('equal', 'replace'):
        for i, j in zip(range(i1, i2), range(j1, j2)):
            if len(ref_nodes[i]["clean"]) < 2 or len(trans_nodes[j]["clean"]) < 2:
                continue
            if count < 5:
                out.append(f"\n--- Pair {count+1} (ref[{i}] vs trans[{j}], offset={j-i}) ---")
                out.append(f"  REF:   {ref_nodes[i]['raw'][:250]}")
                out.append(f"  TRANS: {trans_nodes[j]['raw'][:250]}")
            count += 1

out.append(f"\nTotal comparable segments: {count}")

# Check pairs around the "worst" area (around index 1760, 1761 from the screenshot)
out.append("\n" + "="*80)
out.append("PAIRS NEAR WORST SEGMENTS (around ref index 1760-1770):")
out.append("="*80)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag in ('equal', 'replace'):
        for i, j in zip(range(i1, i2), range(j1, j2)):
            if 1758 <= i <= 1768:
                out.append(f"\n--- ref[{i}] vs trans[{j}] (offset={j-i}) ---")
                out.append(f"  REF RAW:   {ref_nodes[i]['raw'][:300]}")
                out.append(f"  REF CLEAN: {ref_nodes[i]['clean'][:300]}")
                out.append(f"  TRANS RAW:   {trans_nodes[j]['raw'][:300]}")
                out.append(f"  TRANS CLEAN: {trans_nodes[j]['clean'][:300]}")

# Write to file
with open("diagnose_eval_output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))

print("Output written to diagnose_eval_output.txt")
