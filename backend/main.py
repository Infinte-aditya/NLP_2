from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
import shutil
import os
import re
from typing import Dict
import torch

from backend.pipeline.simplification import simplify_text
from backend.utils.docx_utils import translate_docx
from backend.utils.xml_utils import translate_xml
from backend.utils.pdf_gen import generate_pdf
from backend.pipeline.preprocessing import load_glossary, classify_terms, protect_terms
from backend.pipeline.translation import translate_sentences
from backend.pipeline.postprocessing import restore_placeholders
from backend.glossary_updater import GlossaryUpdater
from docx2pdf import convert as docx2pdf_convert

# ── Config ────────────────────────────────────────────────────────────────────

# Glossary lives at project root (one level above backend/)
GLOSSARY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "upg.json"
)

# Single updater instance — shared across all requests
updater = GlossaryUpdater(glossary_path=GLOSSARY_PATH)

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Document Translation Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

progress_state = {"status": "idle", "percent": 0}

# ── Helpers ───────────────────────────────────────────────────────────────────

def update_progress(stage, percent):
    global progress_state
    progress_state["status"] = stage
    progress_state["percent"] = percent

def apply_glossary_post_translation(text: str, glossary: Dict) -> str:
    """Catch English glossary terms that survived translation."""
    sorted_terms = sorted(glossary.keys(), key=len, reverse=True)
    result = text
    for term in sorted_terms:
        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
        result = pattern.sub(glossary[term], result)
    return result

# ── Core Translation Helper ───────────────────────────────────────────────────

def make_translation_helper(target_lang: str, is_docx: bool = False):
    """
    Returns a translation_helper function configured for the given language.
    This is what gets passed to translate_docx() and translate_xml().
    """
    target_lower = target_lang.lower()

    if 'hindi' in target_lower:
        tgt_script = "hi"
    elif any(x in target_lower for x in ("malay", "ms", "bahasa", "zsm")):
        tgt_script = "ms"
    else:
        tgt_script = "ta"


    def translation_helper(sentences, lang, progress_callback=None):

        full_glossary = load_glossary(GLOSSARY_PATH)
        protected_glossary, _ = classify_terms(full_glossary, target_lang)

        final_sentences = [""] * len(sentences)  # pre-allocate result list
        batch_size = 8 if not torch.cuda.is_available() else 192
        total = len(sentences)

        # ── Split into short (≤5 words) and long sentences ───────────────────────
        short_indices, short_sentences = [], []
        long_indices,  long_sentences  = [], []

        for i, s in enumerate(sentences):
            if len(s.split()) <= 5:
                short_indices.append(i)
                short_sentences.append(s)
            else:
                long_indices.append(i)
                long_sentences.append(s)

        print(f"[Pipeline] {len(short_sentences)} short segments (beam=1), "
            f"{len(long_sentences)} long segments (beam=2)")

        # ── Helper: run one group through the full pipeline ───────────────────────
        def process_group(group_sentences, group_indices, num_beams):
            nonlocal full_glossary, protected_glossary

            for i in range(0, len(group_sentences), batch_size):
                batch         = group_sentences[i: i + batch_size]
                batch_indices = group_indices[i: i + batch_size]

                # Step 1: Simplify + Protect
                protected_batch, placeholder_maps = [], []
                for s in batch:
                    simplified = simplify_text(s)
                    prot, ph_map = protect_terms(simplified, protected_glossary)
                    protected_batch.append(prot)
                    placeholder_maps.append(ph_map)

                # Step 2: Translate with the correct beam count
                translated_batch = translate_sentences(
                    protected_batch,
                    target_lang=target_lang,
                    num_beams=num_beams
                )

                # Step 3: Restore + enforce glossary + auto-update
                for j, trans_s in enumerate(translated_batch):
                    original_idx = batch_indices[j]

                    if not trans_s:
                        final_sentences[original_idx] = ""
                        continue

                    restored = restore_placeholders(
                        trans_s,
                        placeholder_maps[j],
                        highlight=is_docx
                    )

                    restored = apply_glossary_post_translation(
                        restored, protected_glossary
                    )


                    is_malay = tgt_script == "ms"
                    if not is_malay:
                        restored, new_terms = updater.process(restored, tgt_script=tgt_script)
                        if new_terms:
                            full_glossary = load_glossary(GLOSSARY_PATH)
                            protected_glossary, _ = classify_terms(full_glossary, target_lang)
                            print(f"[Pipeline] Glossary updated: {new_terms}")

                    final_sentences[original_idx] = restored

                # Progress update
                done = sum(1 for s in final_sentences if s != "")
                if progress_callback:
                    pct = 40 + int((done / total) * 40)
                    progress_callback(
                        f"Translating {done}/{total}...",
                        min(pct, 79)
                    )

        # ── Run both groups ───────────────────────────────────────────────────────
        process_group(short_sentences, short_indices, num_beams=1)  # greedy
        process_group(long_sentences,  long_indices,  num_beams=2)  # fast beam

        return final_sentences
    return translation_helper

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/status")
async def health_check():
    return {"status": "ok", "service": "Backend is running"}

@app.get("/progress")
async def get_progress():
    return progress_state

@app.post("/translate")
def translate_document(
    file: UploadFile = File(...),
    target_lang: str = Form("Tamil"),
    output_format: str = Form("pdf")
):
    global progress_state
    update_progress("Starting...", 0)

    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = f"{upload_dir}/{file.filename}"
    filename_lower = file.filename.lower()

    # Determine output path
    if filename_lower.endswith(".docx"):
        docx_output = f"{upload_dir}/translated_{file.filename}"
        output_filename = (
            f"translated_{os.path.splitext(file.filename)[0]}.pdf"
            if output_format.lower() == "pdf"
            else f"translated_{file.filename}"
        )
    elif filename_lower.endswith(".xml"):
        docx_output = None
        output_filename = f"translated_{file.filename}"
    else:
        docx_output = None
        output_filename = f"translated_{file.filename}.txt"

    output_path = f"{upload_dir}/{output_filename}"

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        update_progress("Loading model and glossary...", 10)

        if filename_lower.endswith(".xml"):
            helper = make_translation_helper(target_lang, is_docx=False)
            translate_xml(
                file_path, output_path, helper, target_lang, update_progress
            )

        elif filename_lower.endswith(".docx"):
            helper = make_translation_helper(target_lang, is_docx=True)
            translate_docx(
                file_path, docx_output, helper, target_lang, update_progress
            )
            if output_format.lower() == "pdf":
                update_progress("Converting to PDF...", 96)
                try:
                    docx2pdf_convert(docx_output, output_path)
                except Exception as pdf_err:
                    print(f"docx2pdf failed: {pdf_err}")
                    output_path = docx_output
                    output_filename = os.path.basename(docx_output)
            else:
                output_path = docx_output

        update_progress("Completed", 100)
        return {
            "filename": file.filename,
            "status": "Translation Complete",
            "download_url": f"/download/{output_filename}"
        }

    except Exception as e:
        update_progress("Error", 0)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = f"uploads/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    if filename.endswith(".xml"):
        media_type = "application/xml"
    elif filename.endswith(".pdf"):
        media_type = "application/pdf"
    elif filename.endswith(".docx"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        media_type = "text/plain"
    return FileResponse(file_path, media_type=media_type, filename=filename)

@app.post("/evaluate")
def evaluate_xml(
    reference: UploadFile = File(...),
    translated: UploadFile = File(...)
):
    import time
    from bs4 import BeautifulSoup
    from backend.pipeline.evaluation import (
        bleu_score, chrf_score, ter_score,
        semantic_score, semantic_score_batch
    )

    def clean_text(text):
        if not text:
            return ""
        text = text.replace("@@", "")
        return re.sub(r'\s+', ' ', text).strip()

    def is_trivial(text):
        if not text or not text.strip():
            return True
        if re.fullmatch(r'[\W_]+', text):
            return True
        return False

    try:
        ref_content = reference.file.read()
        trans_content = translated.file.read()

        ref_soup = BeautifulSoup(ref_content, "xml")
        trans_soup = BeautifulSoup(trans_content, "xml")

        def extract_text_nodes(soup):
            nodes = []
            for tag in soup.find_all(True):
                if tag.string and tag.string.strip():
                    cleaned = clean_text(tag.string)
                    if cleaned:
                        nodes.append({"tag": tag.name, "clean": cleaned})
            return nodes

        ref_nodes = extract_text_nodes(ref_soup)
        trans_nodes = extract_text_nodes(trans_soup)

        ref_full = " ".join(n["clean"] for n in ref_nodes)
        trans_full = " ".join(n["clean"] for n in trans_nodes)

        bleu_result   = bleu_score(trans_full, ref_full)
        chrf_result   = chrf_score(trans_full, ref_full)
        ter_result    = ter_score(trans_full, ref_full)
        sem_result    = semantic_score(trans_full, ref_full)

        import difflib
        sm = difflib.SequenceMatcher(
            None,
            [n["tag"] for n in ref_nodes],
            [n["tag"] for n in trans_nodes]
        )
        aligned_pairs = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag in ('equal', 'replace'):
                for i, j in zip(range(i1, i2), range(j1, j2)):
                    if not is_trivial(ref_nodes[i]["clean"]) and \
                       not is_trivial(trans_nodes[j]["clean"]):
                        aligned_pairs.append((i, j))

        segment_scores = []
        if aligned_pairs:
            all_hyps = [trans_nodes[j]["clean"] for _, j in aligned_pairs]
            all_refs = [ref_nodes[i]["clean"]   for i, _ in aligned_pairs]
            batch_sem = semantic_score_batch(all_hyps, all_refs)

            for idx, (i, j) in enumerate(aligned_pairs):
                seg_chrf = chrf_score(trans_nodes[j]["clean"], ref_nodes[i]["clean"])
                segment_scores.append({
                    "index": i,
                    "ref_preview":   ref_nodes[i]["clean"][:120],
                    "trans_preview": trans_nodes[j]["clean"][:120],
                    "chrf":     round(seg_chrf["chrf"], 2),
                    "semantic": round(batch_sem[idx]["semantic_score"], 2),
                    "tag":      ref_nodes[i]["tag"],
                })

        sorted_scores = sorted(segment_scores, key=lambda x: x["semantic"])
        worst = sorted_scores[:8]
        best  = sorted_scores[-5:][::-1]

        total = max(len(segment_scores), 1)
        good  = sum(1 for s in segment_scores if s["semantic"] >= 75)
        fair  = sum(1 for s in segment_scores if 40 <= s["semantic"] < 75)
        poor  = sum(1 for s in segment_scores if s["semantic"] < 40)
        avg_chrf = sum(s["chrf"] for s in segment_scores) / total

        recommendations = []
        if len(ref_nodes) != len(trans_nodes):
            diff = abs(len(ref_nodes) - len(trans_nodes))
            recommendations.append(
                f"XML NODE COUNT MISMATCH: Reference has {len(ref_nodes)} nodes "
                f"but translation has {len(trans_nodes)} ({diff} differ)."
            )
        if (poor / total) > 0.3:
            recommendations.append(
                f"HIGH PROPORTION OF POOR MATCHES: {poor}/{total} nodes "
                f"({poor/total*100:.0f}%) scored below 40 semantic."
            )
        if (fair / total) > 0.3:
            recommendations.append(
                f"MANY PARTIAL MATCHES: {fair} nodes ({fair/total*100:.0f}%) "
                f"scored 40-75 semantic."
            )
        if (good / total) > 0.5:
            recommendations.append(
                f"GOOD ALIGNMENT: {good} nodes ({good/total*100:.0f}%) "
                f"scored above 75 semantic."
            )

        english_words = re.findall(r'\b[a-zA-Z]{5,}\b', trans_full)
        if len(set(english_words)) > 10:
            sample = ', '.join(list(set(english_words))[:20])
            recommendations.append(
                f"ENGLISH LEAKAGE: {len(set(english_words))} unique English words "
                f"in output: {sample}"
            )

        return {
            "overall_scores": {
                "bleu":     bleu_result["bleu"],
                "chrf":     chrf_result["chrf"],
                "ter":      ter_result["score"],
                "semantic": sem_result["semantic_score"]
            },
            "segment_distribution": {
                "good":              {"count": good, "percentage": round(good/total*100, 1)},
                "fair":              {"count": fair, "percentage": round(fair/total*100, 1)},
                "poor":              {"count": poor, "percentage": round(poor/total*100, 1)},
                "total_comparisons": len(segment_scores),
                "average_chrf":      round(avg_chrf, 2)
            },
            "recommendations":  recommendations,
            "worst_segments":   worst,
            "best_segments":    best,
            "diagnostics": {
                "ref_nodes":   len(ref_nodes),
                "trans_nodes": len(trans_nodes)
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)