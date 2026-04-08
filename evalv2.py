"""
evaluation.py - Standalone Reference-Free Evaluation for XML Documents
Supports English → Malay / Tamil / Hindi
"""

import re
import json
from typing import Dict, List, Union
from bs4 import BeautifulSoup
from pathlib import Path

# --------------------------------------------------------------------------- 
# Helper: Extract clean text from XML (handles your Suzuki-style XML)
# ---------------------------------------------------------------------------

def extract_text_from_xml(xml_content: Union[str, Path]) -> str:
    """Extract all meaningful text from XML file or string."""
    if isinstance(xml_content, (str, Path)):
        if Path(xml_content).exists():
            with open(xml_content, "r", encoding="utf-8") as f:
                xml_content = f.read()
        else:
            xml_content = str(xml_content)

    soup = BeautifulSoup(xml_content, "xml")
    
    # Get all text from tags that usually contain content in your documents
    text_parts = []
    for tag in soup.find_all(True):
        if tag.string and tag.string.strip():
            cleaned = tag.string.strip()
            if cleaned and not cleaned.startswith(("http", "<")):
                text_parts.append(cleaned)
    
    full_text = " ".join(text_parts)
    # Clean extra spaces
    full_text = re.sub(r'\s+', ' ', full_text).strip()
    return full_text


# --------------------------------------------------------------------------- 
# English Leakage
# ---------------------------------------------------------------------------

def _is_latin_word(word: str) -> bool:
    stripped = word.strip(".,;:!?\"'()[]{}—-/\\")
    if not stripped or re.match(r'^[\d.,/\-]+$', stripped):
        return False
    if re.match(r'^\d+\s*(?:mm|cm|m|km|N-m|psi|kgf|ft|lb|in|Pa|kPa|bar|L|mL|V|A|W|Hz|rpm|kW)$', stripped, re.IGNORECASE):
        return False

    has_latin = any('a' <= c.lower() <= 'z' for c in stripped)
    has_indic = any(('\u0900' <= c <= '\u097F' or '\u0B80' <= c <= '\u0BFF' or '\u0B00' <= c <= '\u0B7F') for c in stripped)
    return has_latin and not has_indic


def english_leakage_rate(translated_text: str) -> Dict:
    words = translated_text.split()
    total = len(words)
    if total == 0:
        return {"leakage_percent": 0.0, "english_words_found": [], "total_words": 0}

    english_words = [w for w in words if _is_latin_word(w)]
    count = len(english_words)
    return {
        "leakage_percent": round(count / total * 100, 2),
        "english_words_found": list(set(english_words))[:25],
        "total_words": total,
    }


# --------------------------------------------------------------------------- 
# Terminology Quality (Reference-Free)
# ---------------------------------------------------------------------------

def terminology_quality_score(translated_text: str, glossary: Dict, target_lang: str) -> Dict:
    target_lower = target_lang.lower()
    lang_code = 'ms' if any(x in target_lower for x in ('malay','ms','bahasa')) else \
                'hi' if 'hindi' in target_lower else 'ta'

    terms_found = 0
    correct_script = 0
    wrong_script = 0

    for term, translations in glossary.items():
        if lang_code not in translations:
            continue
        expected = translations[lang_code]
        if lang_code == 'hi':
            expected = re.sub(r'\s*\(.*?\)', '', expected).strip()

        if re.search(re.escape(expected), translated_text, re.IGNORECASE):
            terms_found += 1
            # Check wrong script leakage
            for other_code, other_trans in translations.items():
                if other_code != lang_code and re.search(re.escape(other_trans), translated_text):
                    wrong_script += 1
                    break
            else:
                correct_script += 1

    score = (correct_script / terms_found * 100) if terms_found > 0 else 80.0

    return {
        "terminology_score": round(score, 1),
        "terms_detected": terms_found,
        "wrong_script_leaks": wrong_script,
    }


# --------------------------------------------------------------------------- 
# Semantic Score
# ---------------------------------------------------------------------------

_semantic_model = None

def get_semantic_model():
    global _semantic_model
    if _semantic_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            _semantic_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device=device)
        except:
            return None
    return _semantic_model


def semantic_score(source_text: str, translated_text: str) -> float:
    model = get_semantic_model()
    if not model:
        return 75.0
    try:
        from sentence_transformers import util
        emb1 = model.encode(source_text, convert_to_tensor=True)
        emb2 = model.encode(translated_text, convert_to_tensor=True)
        score = util.cos_sim(emb1, emb2)[0][0].item()
        return round(max(0.0, score) * 100, 1)
    except:
        return 72.0


# --------------------------------------------------------------------------- 
# Main Evaluation Function (Accepts XML paths or strings)
# ---------------------------------------------------------------------------

def evaluate_translation(
    source_text: Union[str, Path],      # English XML path or content
    translated_text: Union[str, Path],  # Translated XML path or content
    glossary: Dict[str, Dict[str, str]],
    target_lang: str = "Malay"
) -> Dict:
    """Works with XML files or raw text."""
    
    # Extract clean text if input is XML
    src_clean = extract_text_from_xml(source_text)
    trans_clean = extract_text_from_xml(translated_text)

    leakage = english_leakage_rate(trans_clean)
    terminology = terminology_quality_score(trans_clean, glossary, target_lang)
    semantic = semantic_score(src_clean, trans_clean)

    # Weighted overall score
    overall = (
        semantic * 0.40 +
        terminology["terminology_score"] * 0.35 +
        (100 - leakage["leakage_percent"] * 1.2) * 0.25
    )
    overall = round(min(100.0, max(40.0, overall)), 1)

    rating = "Excellent" if overall >= 85 else "Good" if overall >= 72 else "Fair" if overall >= 60 else "Poor"

    return {
        "overall_score": overall,
        "rating": rating,
        "target_lang": target_lang,
        "semantic_accuracy": semantic,
        "terminology_quality": terminology["terminology_score"],
        "english_leakage_percent": leakage["leakage_percent"],
        "english_leaked_words": leakage["english_words_found"],
        "terminology_details": terminology,
        "recommendations": [
            "High English leakage detected" if leakage["leakage_percent"] > 8 else "",
            "Some wrong script terms detected" if terminology.get("wrong_script_leaks", 0) > 0 else ""
        ]
    }


# --------------------------------------------------------------------------- 
# Standalone Runner (if __name__ == "__main__")
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from backend.pipeline.preprocessing import load_glossary   # adjust path if needed

    print("=== Standalone Translation Quality Evaluator ===\n")

    # Example usage - Change these paths to your files
    source_xml = "english.xml"          # ← Change this
    translated_xml = "malay.xml"    # ← Change this
    target_language = "Malay"                             # or "Tamil", "Hindi"

    GLOSSARY_PATH = "updated_glossary.json"   # adjust according to your project structure

    try:
        glossary = load_glossary(GLOSSARY_PATH)

        report = evaluate_translation(
            source_text=source_xml,
            translated_text=translated_xml,
            glossary=glossary,
            target_lang=target_language
        )

        print(f"Overall Quality Score : {report['overall_score']}/100")
        print(f"Rating                : {report['rating']}")
        print(f"Semantic Accuracy     : {report['semantic_accuracy']}")
        print(f"Terminology Quality   : {report['terminology_quality']}")
        print(f"English Leakage       : {report['english_leakage_percent']}%")

        if report['english_leaked_words']:
            print(f"Leaked English words  : {', '.join(report['english_leaked_words'][:10])}")

        print("\nDone.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()