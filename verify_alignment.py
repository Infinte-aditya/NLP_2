import asyncio
from bs4 import BeautifulSoup
from fastapi import UploadFile
import os

# We will just run the core evaluate_xml logic manually to see if it aligns correctly
def strip_to_indic_only(text: str) -> str:
    import re
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
            # KEEP the node even if 'clean' is empty/short
            nodes.append({"raw": raw, "clean": clean, "tag": tag.name})
    return nodes

with open("uploads/english.xml", "rb") as f:
    ref_soup = BeautifulSoup(f.read().decode("utf-8", errors="replace"), "xml")

with open("uploads/translated_english.xml", "rb") as f:
    trans_soup = BeautifulSoup(f.read().decode("utf-8", errors="replace"), "xml")

ref_nodes = extract_text_nodes(ref_soup)
trans_nodes = extract_text_nodes(trans_soup)

print(f"Reference nodes: {len(ref_nodes)}")
print(f"Translated nodes: {len(trans_nodes)}")

import difflib
ref_tags = [n["tag"] for n in ref_nodes]
trans_tags = [n["tag"] for n in trans_nodes]

sm = difflib.SequenceMatcher(None, ref_tags, trans_tags)

found = False
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag in ('equal', 'replace'):
        for i, j in zip(range(i1, i2), range(j1, j2)):
            ref_clean = ref_nodes[i]["clean"]
            trans_clean = trans_nodes[j]["clean"]
            
            # Print specifically where "கண்டறியப்படவில்லை" comes from
            if "கண்டறியப்படவில்லை" in trans_clean or "கண்டறியப்படவில்லை" in ref_clean:
                print(f"Match found at index {i} -> {j}")
                print(f"  Reference  : {ref_clean}")
                print(f"  Translation: {trans_clean}")
                print(f"  Ref Raw    : {ref_nodes[i]['raw']}")
                print(f"  Trans Raw  : {trans_nodes[j]['raw']}")
                print("-" * 40)
                found = True

if not found:
    print("Could not find the target string in alignment.")
