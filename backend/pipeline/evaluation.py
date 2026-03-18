"""
evaluation.py
=============
Translation quality evaluation metrics for the NLP Automotive Translation pipeline.

Metrics implemented:
1. Glossary Term Coverage Rate  - % of glossary terms correctly transliterated
2. English Word Leakage Rate    - % of English words remaining in translated output
3. BLEU Score                   - Requires reference translations
4. chrF Score                   - Character-level F-score (recommended for Tamil/Hindi)
5. TER Score                    - Translation Edit Rate (requires reference translations)
6. Per-Sentence Evaluation      - Sentence-level detailed report
"""

import re
import json
import unicodedata
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher


# ---------------------------------------------------------------------------
# 1. English Word Leakage Rate
# ---------------------------------------------------------------------------

def _is_latin_word(word: str) -> bool:
    """
    Returns True if the word consists primarily of Latin/ASCII characters
    (i.e., it is an English word that should have been translated).
    Excludes: numbers, measurement units, technical codes (e.g. N-m, kPa, mm).
    """
    # Strip punctuation around the word
    stripped = word.strip(".,;:!?\"'()[]{}—-/\\")
    if not stripped:
        return False
    # Numbers, measurement units, codes → not "English leakage"
    if re.match(r'^[\d.,/\-]+$', stripped):
        return False
    # Allow pure technical codes / measurement units
    if re.match(r'^\d+\s*(?:mm|cm|m|km|N-m|psi|kgf|ft|lb|in|Pa|kPa|bar|L|mL|V|A|W|Hz|rpm|kW)$', stripped, re.IGNORECASE):
        return False
    # A word is "English" if it contains only ASCII letters (no Indic script)
    has_latin = any('a' <= c.lower() <= 'z' for c in stripped)
    has_indic = any(
        '\u0900' <= c <= '\u097F' or  # Devanagari (Hindi)
        '\u0B80' <= c <= '\u0BFF'     # Tamil
        for c in stripped
    )
    return has_latin and not has_indic


def english_leakage_rate(translated_text: str) -> Dict:
    """
    Computes the English Word Leakage Rate for a translated text.
    
    Returns:
        {
            "leakage_rate": float,          # 0.0 - 1.0 (lower is better)
            "leakage_percent": float,       # 0-100% display value
            "english_words_found": list,    # list of leaked English words
            "total_words": int,
            "english_word_count": int,
        }
    """
    words = translated_text.split()
    total_words = len(words)
    if total_words == 0:
        return {"leakage_rate": 0.0, "leakage_percent": 0.0, "english_words_found": [], 
                "total_words": 0, "english_word_count": 0}

    english_words = [w for w in words if _is_latin_word(w)]
    count = len(english_words)
    rate = count / total_words

    return {
        "leakage_rate": round(rate, 4),
        "leakage_percent": round(rate * 100, 2),
        "english_words_found": list(set(english_words)),  # unique
        "total_words": total_words,
        "english_word_count": count,
    }


# ---------------------------------------------------------------------------
# 2. Glossary Term Coverage Rate
# ---------------------------------------------------------------------------

def glossary_coverage_rate(
    source_text: str,
    translated_text: str,
    glossary: Dict[str, Dict[str, str]],
    target_lang: str,
) -> Dict:
    """
    Measures what percentage of glossary terms present in the source were
    correctly transliterated (using glossary values) in the translated output.

    Args:
        source_text:     Original English text
        translated_text: Translated Tamil/Hindi text
        glossary:        The full english_tamil_hindi_glossary dict
        target_lang:     'ta' (Tamil) or 'hi' (Hindi) or 'Tamil'/'Hindi'

    Returns:
        {
            "coverage_rate": float,         # 0.0–1.0 (higher is better)
            "coverage_percent": float,      # display value
            "terms_found_in_source": list,  # glossary terms that appeared in source
            "terms_correctly_translated": list,
            "terms_missed": list,           # terms in source but NOT in output
        }
    """
    lang_code = 'ta' if 'tamil' in target_lang.lower() else 'hi'

    terms_in_source = []
    terms_correct = []
    terms_missed = []

    # Sort by key length desc to match longest terms first
    sorted_terms = sorted(glossary.keys(), key=len, reverse=True)

    for term in sorted_terms:
        if lang_code not in glossary[term]:
            continue
        expected_translation = glossary[term][lang_code]
        # Clean Hindi parenthetical e.g. "एअर बॅग(Air Bag)" → "एअर बॅग"
        expected_translation = re.sub(r'\s*\(.*?\)', '', expected_translation).strip()

        # Check if English term appears in source
        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
        if not pattern.search(source_text):
            continue

        terms_in_source.append(term)

        # Check if expected translation appears in translated output
        if expected_translation in translated_text:
            terms_correct.append(term)
        else:
            terms_missed.append(term)

    total = len(terms_in_source)
    correct = len(terms_correct)
    rate = correct / total if total > 0 else 1.0  # 100% if no terms in source

    return {
        "coverage_rate": round(rate, 4),
        "coverage_percent": round(rate * 100, 2),
        "terms_found_in_source": terms_in_source,
        "terms_correctly_translated": terms_correct,
        "terms_missed": terms_missed,
        "total_glossary_terms_in_source": total,
        "correctly_translated_count": correct,
    }


# ---------------------------------------------------------------------------
# 3. BLEU Score (sentence-level)
# ---------------------------------------------------------------------------

def _get_ngrams(tokens: List[str], n: int) -> Dict[tuple, int]:
    """Count n-grams in token list."""
    ngrams: Dict[tuple, int] = {}
    for i in range(len(tokens) - n + 1):
        gram = tuple(tokens[i:i + n])
        ngrams[gram] = ngrams.get(gram, 0) + 1
    return ngrams


def bleu_score(
    hypothesis: str,
    reference: str,
    max_n: int = 4,
) -> Dict:
    """
    Computes sentence-level BLEU score.

    Args:
        hypothesis:  Machine translated text
        reference:   Human reference translation
        max_n:       Maximum n-gram order (default 4 for BLEU-4)

    Returns:
        {
            "bleu": float,          # 0.0–100.0
            "precisions": list,     # precision for each n-gram order
            "brevity_penalty": float,
        }
    """
    import math

    hyp_tokens = hypothesis.split()
    ref_tokens = reference.split()

    if not hyp_tokens:
        return {"bleu": 0.0, "precisions": [], "brevity_penalty": 0.0}

    precisions = []
    for n in range(1, max_n + 1):
        hyp_ngrams = _get_ngrams(hyp_tokens, n)
        ref_ngrams = _get_ngrams(ref_tokens, n)

        clipped_count = 0
        total_hyp = sum(hyp_ngrams.values())

        for gram, count in hyp_ngrams.items():
            clipped_count += min(count, ref_ngrams.get(gram, 0))

        precision = clipped_count / total_hyp if total_hyp > 0 else 0
        precisions.append(precision)

    # Geometric mean of precisions
    if all(p > 0 for p in precisions):
        log_avg = sum(math.log(p) for p in precisions) / max_n
        geo_mean = math.exp(log_avg)
    else:
        geo_mean = 0.0

    # Brevity penalty
    hyp_len = len(hyp_tokens)
    ref_len = len(ref_tokens)
    if hyp_len >= ref_len:
        bp = 1.0
    else:
        bp = math.exp(1 - ref_len / hyp_len) if hyp_len > 0 else 0.0

    bleu = bp * geo_mean * 100

    return {
        "bleu": round(bleu, 2),
        "precisions": [round(p * 100, 2) for p in precisions],
        "brevity_penalty": round(bp, 4),
    }


# ---------------------------------------------------------------------------
# 4. chrF Score (character-level F-score) — recommended for Tamil/Hindi
# ---------------------------------------------------------------------------

def chrf_score(
    hypothesis: str,
    reference: str,
    n: int = 6,
    beta: float = 2.0,
) -> Dict:
    """
    Computes chrF score (character n-gram F-score).
    Particularly better than BLEU for morphologically rich languages (Tamil, Hindi).

    Args:
        hypothesis:  Machine translated text
        reference:   Human reference translation
        n:           Character n-gram order (default 6)
        beta:        Weight for recall vs precision (default 2.0 = F2, recall-weighted)

    Returns:
        {
            "chrf": float,          # 0.0–100.0 (higher is better)
            "precision": float,
            "recall": float,
        }
    """
    def char_ngrams(text: str, n: int) -> Dict[str, int]:
        ngrams: Dict[str, int] = {}
        # Include spaces for context
        for i in range(len(text) - n + 1):
            gram = text[i:i + n]
            ngrams[gram] = ngrams.get(gram, 0) + 1
        return ngrams

    hyp_ngrams = char_ngrams(hypothesis, n)
    ref_ngrams = char_ngrams(reference, n)

    matches = sum(min(count, ref_ngrams.get(gram, 0)) for gram, count in hyp_ngrams.items())

    total_hyp = sum(hyp_ngrams.values())
    total_ref = sum(ref_ngrams.values())

    precision = matches / total_hyp if total_hyp > 0 else 0.0
    recall = matches / total_ref if total_ref > 0 else 0.0

    if precision + recall > 0:
        chrf = (1 + beta**2) * precision * recall / (beta**2 * precision + recall)
    else:
        chrf = 0.0

    return {
        "chrf": round(chrf * 100, 2),
        "precision": round(precision * 100, 2),
        "recall": round(recall * 100, 2),
    }


# ---------------------------------------------------------------------------
# 5. TER – Translation Edit Rate
# ---------------------------------------------------------------------------

def ter_score(hypothesis: str, reference: str) -> Dict:
    """
    Computes TER (Translation Edit Rate).
    TER = #edits / reference_length. Lower is better (0 = perfect).

    Uses simple edit distance (insertions, deletions, substitutions).
    Does not include shifts (simplified TER).

    Returns:
        {
            "ter": float,       # 0.0+ (lower is better, 0 = perfect match)
            "edit_distance": int,
            "reference_length": int,
        }
    """
    hyp_tokens = hypothesis.split()
    ref_tokens = reference.split()

    ref_len = len(ref_tokens)
    if ref_len == 0:
        return {"ter": 0.0, "edit_distance": 0, "reference_length": 0}

    # Levenshtein edit distance on token lists
    m, n = len(hyp_tokens), len(ref_tokens)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if hyp_tokens[i - 1] == ref_tokens[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

    edit_dist = dp[m][n]
    ter = edit_dist / ref_len

    return {
        "ter": round(ter, 4),
        "edit_distance": edit_dist,
        "reference_length": ref_len,
    }


# ---------------------------------------------------------------------------
# 6. Semantic Similarity Score (AI Meaning Based)
# ---------------------------------------------------------------------------

_semantic_model = None

def get_semantic_model():
    """Lazy load the sentence transformer model so it only loads into memory when needed."""
    global _semantic_model
    if _semantic_model is None:
        try:
            import torch
            from sentence_transformers import SentenceTransformer
            # Lightweight multilingual model (Supports English, Tamil, Hindi, etc.)
            # Generates mathematical vectors of meaning.
            device = "cuda" if torch.cuda.is_available() else "cpu"
            _semantic_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device=device)
        except ImportError:
            print("WARNING: sentence-transformers not installed. Semantic scoring disabled.")
            return None
    return _semantic_model

def semantic_score(hypothesis: str, reference: str) -> Dict:
    """
    Computes Semantic Similarity Score between hypothesis and reference.
    Instead of checking if characters match, this checks if the AI *understands* 
    them to mean the same thing. Resolves issues with synonym variance.
    
    Returns:
        { "semantic_score": float }  # 0.0 to 100.0
    """
    model = get_semantic_model()
    
    if not model or not hypothesis.strip() or not reference.strip():
        return {"semantic_score": 0.0}
        
    from sentence_transformers import util
    import torch
    
    # Extract the Meaning Vectors
    emb_hyp = model.encode(hypothesis, convert_to_tensor=True)
    emb_ref = model.encode(reference, convert_to_tensor=True)
    
    # Calculate angular distance (Cosine Similarity)
    cos_sim = util.cos_sim(emb_hyp, emb_ref)
    
    # Convert from [-1, 1] to [0, 100] scale
    score = float(cos_sim[0][0])
    score = max(0.0, score) * 100.0
    
    return {"semantic_score": round(score, 2)}


def semantic_score_batch(hypotheses: List[str], references: List[str]) -> List[Dict]:
    """
    Batch version of semantic_score — encodes ALL texts at once for massive speedup.
    """
    model = get_semantic_model()
    
    if not model or len(hypotheses) != len(references):
        return [{"semantic_score": 0.0}] * len(hypotheses)
    
    from sentence_transformers import util
    import torch
    
    valid_indices = []
    valid_hyps = []
    valid_refs = []
    for i, (h, r) in enumerate(zip(hypotheses, references)):
        if h.strip() and r.strip():
            valid_indices.append(i)
            valid_hyps.append(h)
            valid_refs.append(r)
    
    results = [{"semantic_score": 0.0}] * len(hypotheses)
    
    if not valid_hyps:
        return results
    
    BATCH_SIZE = 256
    all_scores = [0.0] * len(valid_hyps)
    
    for start in range(0, len(valid_hyps), BATCH_SIZE):
        end = min(start + BATCH_SIZE, len(valid_hyps))
        batch_hyps = valid_hyps[start:end]
        batch_refs = valid_refs[start:end]
        
        emb_hyps = model.encode(batch_hyps, convert_to_tensor=True, show_progress_bar=False)
        emb_refs = model.encode(batch_refs, convert_to_tensor=True, show_progress_bar=False)
        
        cos_sims = util.cos_sim(emb_hyps, emb_refs)
        
        for k in range(len(batch_hyps)):
            score = float(cos_sims[k][k])
            all_scores[start + k] = max(0.0, score) * 100.0
    
    for idx, orig_idx in enumerate(valid_indices):
        results[orig_idx] = {"semantic_score": round(all_scores[idx], 2)}
    
    return results


    for idx, orig_idx in enumerate(valid_indices):
        results[orig_idx] = {"semantic_score": round(all_scores[idx], 2)}
    
    return results


# ---------------------------------------------------------------------------
# 7. Full Document Evaluation Report
# ---------------------------------------------------------------------------

def evaluate_document(
    source_segments: List[str],
    translated_segments: List[str],
    glossary: Dict[str, Dict[str, str]],
    target_lang: str,
    reference_segments: Optional[List[str]] = None,
) -> Dict:
    """
    Runs all available metrics on a full document.

    Args:
        source_segments:      List of original English text segments
        translated_segments:  List of translated output segments
        glossary:             Full glossary dict
        target_lang:          'Tamil' or 'Hindi'
        reference_segments:   (Optional) Human reference translations for BLEU/chrF/TER

    Returns: Comprehensive evaluation report dict.
    """
    full_source = " ".join(source_segments)
    full_translated = " ".join(translated_segments)

    report = {}

    # --- English Leakage ---
    leakage = english_leakage_rate(full_translated)
    report["english_leakage"] = leakage

    # --- Glossary Coverage ---
    coverage = glossary_coverage_rate(full_source, full_translated, glossary, target_lang)
    report["glossary_coverage"] = coverage

    # --- Reference-based metrics (only if references provided) ---
    if reference_segments and len(reference_segments) == len(translated_segments):
        full_reference = " ".join(reference_segments)
        report["bleu"] = bleu_score(full_translated, full_reference)
        report["chrf"] = chrf_score(full_translated, full_reference)
        report["ter"] = ter_score(full_translated, full_reference)

        # Per-sentence scores
        per_sentence = []
        for i, (hyp, ref) in enumerate(zip(translated_segments, reference_segments)):
            src = source_segments[i] if i < len(source_segments) else ""
            per_sentence.append({
                "segment_id": i + 1,
                "source": src,
                "hypothesis": hyp,
                "reference": ref,
                "bleu": bleu_score(hyp, ref)["bleu"],
                "chrf": chrf_score(hyp, ref)["chrf"],
                "ter": ter_score(hyp, ref)["ter"],
                "leakage": english_leakage_rate(hyp)["leakage_percent"],
            })
        report["per_sentence"] = per_sentence
    else:
        # No reference → still do per-sentence leakage
        per_sentence = []
        for i, hyp in enumerate(translated_segments):
            src = source_segments[i] if i < len(source_segments) else ""
            per_sentence.append({
                "segment_id": i + 1,
                "source": src,
                "hypothesis": hyp,
                "leakage": english_leakage_rate(hyp)["leakage_percent"],
                "leaked_words": english_leakage_rate(hyp)["english_words_found"],
            })
        report["per_sentence"] = per_sentence

    # --- Summary ---
    report["summary"] = {
        "target_language": target_lang,
        "total_segments": len(translated_segments),
        "glossary_coverage_percent": coverage["coverage_percent"],
        "english_leakage_percent": leakage["leakage_percent"],
        "terms_missed": coverage["terms_missed"],
        "top_leaked_words": leakage["english_words_found"][:20],
    }

    return report


# ---------------------------------------------------------------------------
# 7. CLI / Standalone runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    """
    Quick standalone test.
    Usage:  python -m backend.pipeline.evaluation
    """
    import sys

    # Load glossary
    glossary_path = "english_tamil_hindi_glossary.json"
    try:
        with open(glossary_path, encoding="utf-8") as f:
            glossary = json.load(f)
    except FileNotFoundError:
        print(f"Glossary not found at {glossary_path}. Run from project root.")
        sys.exit(1)

    # Example test
    source = "Check the Oil Filter and inspect the Brake Pad. On-Vehicle Inspection of the Coolant level."
    translated_tamil = "ஆயில் பில்ட்டர் மற்றும் ப்ரேக் பாட் ஐ சரிபாருங்கள். On-Vehicle Inspection of the Coolant level."

    print("=" * 60)
    print("EVALUATION DEMO")
    print("=" * 60)

    print("\n[1] English Leakage Rate:")
    leakage = english_leakage_rate(translated_tamil)
    print(f"  Leakage: {leakage['leakage_percent']}%")
    print(f"  Leaked words: {leakage['english_words_found']}")

    print("\n[2] Glossary Coverage:")
    coverage = glossary_coverage_rate(source, translated_tamil, glossary, "Tamil")
    print(f"  Coverage: {coverage['coverage_percent']}%")
    print(f"  Terms found in source: {coverage['terms_found_in_source']}")
    print(f"  Terms correctly translated: {coverage['terms_correctly_translated']}")
    print(f"  Terms MISSED: {coverage['terms_missed']}")

    print("\n[3] BLEU (example with dummy reference):")
    ref = "ஆயில் பில்ட்டர் மற்றும் ப்ரேக் பாட் சரிபாருங்கள். கூலன்ட் அளவு வாகன பரிசோதனை."
    b = bleu_score(translated_tamil, ref)
    print(f"  BLEU-4: {b['bleu']}")

    print("\n[4] chrF:")
    c = chrf_score(translated_tamil, ref)
    print(f"  chrF: {c['chrf']}")

    print("\nDone.")
