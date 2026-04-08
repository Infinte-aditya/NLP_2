"""
evaluation.py — Reference-Free Translation Quality Evaluator
English → Malay (Automotive Technical Documents)

Metrics
-------
1. Semantic Accuracy     — multilingual sentence-transformer cosine similarity
                           (sentence-level + document-level, averaged)
2. Terminology Quality   — glossary hit rate with wrong-script leak penalty
3. English Leakage       — % unwanted English words left untranslated
4. Fluency / Structure   — Malay word density, sentence-length ratio,
                           common Malay function-word presence
5. Coverage Ratio        — translated length vs source length (guards under/over translation)

Overall = weighted blend, fully normalised to 100.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants & Whitelists
# ---------------------------------------------------------------------------

# Automotive technical terms that are legitimately kept in English inside
# Malay technical manuals (loanwords, brand-neutral jargon, acronyms).
MALAY_TECH_WHITELIST: frozenset[str] = frozenset({
    # Drivetrain / transmission
    "manual", "automatic", "transmission", "transmisi", "cvt", "dct", "amt",
    "4wd", "2wd", "awd", "fwd", "rwd", "4x4",
    # Engine & electrics
    "engine", "enjin", "motor", "alternator", "starter", "ignition",
    "spark", "plug", "injector", "throttle", "turbo", "intercooler",
    "ecu", "tcm", "pcm", "bcm", "abs", "esc", "eps", "hvac",
    "obd", "dtc", "pid",
    # Electronics / sensors
    "sensor", "actuator", "relay", "fuse", "fusebox", "switch", "button",
    "module", "unit", "controller", "display", "lcd", "led",
    "connector", "terminal", "harness", "wiring", "pendawaian",
    "cable", "colok", "plug", "socket",
    # Chassis & brakes
    "brake", "caliper", "rotor", "disc", "drum", "abs", "ebv", "ebd",
    "strut", "shock", "absorber", "bearing", "bushing", "ball", "joint",
    "tie", "rod", "rack", "pinion",
    # Fluids & consumables
    "coolant", "antifreeze", "atf", "mtf", "dot", "psi", "bar", "nm",
    "torque", "rpm", "idle",
    # Common procedure words kept in Malay manuals
    "check", "inspect", "test", "scan", "reset", "calibrate", "bleed",
    "flush", "drain", "refill", "tighten", "torque", "adjust",
    # Assembly / parts
    "assembly", "sub-assembly", "kit", "clip", "bolt", "nut", "screw",
    "washer", "gasket", "seal", "o-ring", "bearing", "pin",
    "bracket", "panel", "trim",
    # Documentation
    "note", "warning", "caution", "tip", "fig", "figure",
    "procedure", "step", "torque", "spec", "specification",
    # Units & measures
    "mm", "cm", "kg", "kpa", "mpa", "v", "a", "ohm", "hz",
    "ms", "rpm", "nm", "liter", "litre",
    # Software / diagnostic tools
    "software", "firmware", "tool", "scanner", "multimeter", "oscilloscope",
})

# High-frequency Malay function words — presence boosts fluency score
MALAY_FUNCTION_WORDS: frozenset[str] = frozenset({
    "yang", "dan", "di", "ke", "dari", "pada", "dengan", "untuk",
    "adalah", "ialah", "ini", "itu", "atau", "jika", "apabila",
    "setelah", "sebelum", "semasa", "oleh", "tidak", "boleh",
    "perlu", "harus", "akan", "telah", "sudah", "juga", "sahaja",
    "serta", "dalam", "antara", "seperti", "bagi", "melalui",
    "kepada", "tentang", "supaya", "agar", "tetapi", "namun",
    "maka", "iaitu", "tersebut", "selain", "menggunakan",
    "pastikan", "periksa", "ganti", "pasang", "keluarkan",
    "tanggalkan", "laraskan", "bersihkan", "semak",
})

# Malay prefixes common in technical writing
MALAY_PREFIXES = re.compile(
    r'^(me|mem|men|meng|meny|ber|per|ter|ke|se|di|pem|pen|peng|peny|pel|pe)\w{3,}$'
)

# Score weight configuration — must sum to 1.0
WEIGHTS = {
    "semantic":      0.40,
    "terminology":   0.30,
    "fluency":       0.15,
    "leakage":       0.10,
    "coverage":      0.05,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "Weights must sum to 1.0"

RATING_THRESHOLDS = [
    (90, "Excellent ✦"),
    (78, "Good"),
    (62, "Fair"),
    (0,  "Poor — Needs Revision"),
]


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class LeakageResult:
    leakage_percent: float
    leaked_words: List[str]
    total_words: int
    leakage_score: float          # 0–100 (100 = no leakage)

@dataclass
class TerminologyResult:
    terminology_score: float      # 0–100
    terms_checked: int
    terms_found: int
    wrong_script_leaks: int
    missing_terms: List[str]

@dataclass
class FluencyResult:
    fluency_score: float          # 0–100
    malay_word_density: float     # % words that look Malay
    function_word_density: float  # % tokens that are Malay function words
    avg_sentence_length: float    # words per sentence
    sentence_count: int

@dataclass
class CoverageResult:
    coverage_score: float         # 0–100
    length_ratio: float           # translated_words / source_words
    source_words: int
    translated_words: int

@dataclass
class EvaluationReport:
    overall_score: float
    rating: str
    target_lang: str
    semantic_accuracy: float
    terminology: TerminologyResult
    fluency: FluencyResult
    leakage: LeakageResult
    coverage: CoverageResult
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

    def summary(self) -> str:
        lines = [
            f"\n{'='*58}",
            f"  Translation Quality Report  ({self.target_lang})",
            f"{'='*58}",
            f"  Overall Score      : {self.overall_score:>5.1f} / 100  [{self.rating}]",
            f"{'─'*58}",
            f"  Semantic Accuracy  : {self.semantic_accuracy:>5.1f}",
            f"  Terminology        : {self.terminology.terminology_score:>5.1f}  "
            f"({self.terminology.terms_found}/{self.terminology.terms_checked} terms matched)",
            f"  Fluency            : {self.fluency.fluency_score:>5.1f}  "
            f"(Malay density {self.fluency.malay_word_density:.0f}%)",
            f"  Leakage            : {self.leakage.leakage_score:>5.1f}  "
            f"({self.leakage.leakage_percent:.1f}% leaked)",
            f"  Coverage           : {self.coverage.coverage_score:>5.1f}  "
            f"(ratio {self.coverage.length_ratio:.2f})",
        ]
        if self.leakage.leaked_words:
            sample = ", ".join(self.leakage.leaked_words[:12])
            lines.append(f"  Leaked words       : {sample}")
        if self.terminology.missing_terms:
            sample = ", ".join(self.terminology.missing_terms[:8])
            lines.append(f"  Missing terms      : {sample}")
        if self.recommendations:
            lines.append(f"{'─'*58}")
            lines.append("  Recommendations:")
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"    {i}. {rec}")
        lines.append(f"{'='*58}\n")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# XML / Text Extraction
# ---------------------------------------------------------------------------

def extract_text_from_xml(xml_input: Union[str, Path]) -> str:
    """
    Extract clean text from an XML file or raw XML string.
    Preserves sentence boundaries with '. ' so sentence-level
    semantic splitting works correctly.
    """
    path = Path(xml_input) if isinstance(xml_input, (str, Path)) else None
    if path and path.exists():
        xml_content = path.read_text(encoding="utf-8")
    else:
        xml_content = str(xml_input)

    soup = BeautifulSoup(xml_content, "xml")
    parts: List[str] = []
    for tag in soup.find_all(True):
        if tag.string and tag.string.strip():
            cleaned = re.sub(r'\s+', ' ', tag.string.strip())
            if cleaned:
                parts.append(cleaned)

    # Join segments with '. ' so downstream sentence-splitting doesn't merge them
    text = ". ".join(parts)
    return re.sub(r'\.\s*\.', '.', text).strip()   # collapse double dots


def split_sentences(text: str) -> List[str]:
    """
    Simple sentence splitter suitable for technical text.
    Falls back to splitting on '. ' and similar delimiters.
    """
    raw = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in raw if len(s.strip()) > 10]


# ---------------------------------------------------------------------------
# 1. Semantic Accuracy
# ---------------------------------------------------------------------------

_semantic_model = None

def _get_model():
    global _semantic_model
    if _semantic_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            log.info("Loading multilingual sentence-transformer on %s …", device)
            # LaBSE gives much better multilingual (especially low-resource) alignment
            # than paraphrase-multilingual-MiniLM-L12-v2
            try:
                _semantic_model = SentenceTransformer("sentence-transformers/LaBSE", device=device)
                log.info("Loaded LaBSE model.")
            except Exception:
                _semantic_model = SentenceTransformer(
                    "paraphrase-multilingual-MiniLM-L12-v2", device=device
                )
                log.info("Loaded fallback MiniLM model.")
        except ImportError:
            log.warning("sentence-transformers not installed. Semantic score will be estimated.")
            return None
    return _semantic_model


def semantic_accuracy(source_text: str, translated_text: str) -> float:
    """
    Compute semantic similarity at both document and sentence level.
    Returns a score 0–100.

    - Document-level: single cosine similarity of full-text embeddings.
    - Sentence-level: average of aligned sentence-pair similarities
      (handles cases where document embeddings wash out local errors).
    - Final = 0.5 * doc_score + 0.5 * sentence_avg
    """
    model = _get_model()
    if model is None:
        return 72.0

    try:
        from sentence_transformers import util
        import torch

        # — Document level —
        emb_src = model.encode(source_text, convert_to_tensor=True)
        emb_tgt = model.encode(translated_text, convert_to_tensor=True)
        doc_score = float(util.cos_sim(emb_src, emb_tgt)[0][0]) * 100

        # — Sentence level —
        src_sents = split_sentences(source_text)
        tgt_sents = split_sentences(translated_text)

        sent_score = doc_score  # fallback if not enough sentences
        if len(src_sents) >= 2 and len(tgt_sents) >= 2:
            # Align by minimum length (zip) to avoid index mismatch
            pairs = list(zip(src_sents, tgt_sents))[:50]  # cap at 50 for speed
            src_embs = model.encode([p[0] for p in pairs], convert_to_tensor=True, batch_size=32)
            tgt_embs = model.encode([p[1] for p in pairs], convert_to_tensor=True, batch_size=32)
            sims = util.cos_sim(src_embs, tgt_embs)
            # Diagonal = aligned pairs
            diag = torch.diagonal(sims).tolist()
            sent_score = sum(max(0.0, s) for s in diag) / len(diag) * 100

        final = 0.5 * doc_score + 0.5 * sent_score
        return round(min(100.0, max(0.0, final)), 2)

    except Exception as exc:
        log.warning("Semantic scoring failed: %s", exc)
        return 70.0


# ---------------------------------------------------------------------------
# 2. Terminology Quality
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text.lower().strip())


def terminology_quality(
    translated_text: str,
    glossary: Dict[str, Dict[str, str]],
    lang_code: str = "ms",
) -> TerminologyResult:
    """
    Check glossary term coverage in the translated text.
    Penalises wrong-script leaks (e.g. Hindi term appearing in a Malay translation).
    """
    trans_norm = _normalize(translated_text)
    terms_checked = 0
    terms_found = 0
    wrong_script_leaks = 0
    missing: List[str] = []

    for source_term, translations in glossary.items():
        if lang_code not in translations:
            continue
        terms_checked += 1
        expected = _normalize(re.sub(r'\s*\(.*?\)', '', translations[lang_code]))

        if re.search(re.escape(expected), trans_norm):
            terms_found += 1
            # Check if a translation for a *different* language also appears
            for other_code, other_trans in translations.items():
                if other_code == lang_code:
                    continue
                other_norm = _normalize(re.sub(r'\s*\(.*?\)', '', other_trans))
                if len(other_norm) > 2 and re.search(re.escape(other_norm), trans_norm):
                    wrong_script_leaks += 1
                    break
        else:
            missing.append(source_term)

    if terms_checked == 0:
        score = 80.0
    else:
        hit_rate = terms_found / terms_checked
        leak_penalty = min(wrong_script_leaks * 3, 20)        # max 20-point penalty
        score = max(0.0, hit_rate * 100 - leak_penalty)

    return TerminologyResult(
        terminology_score=round(score, 1),
        terms_checked=terms_checked,
        terms_found=terms_found,
        wrong_script_leaks=wrong_script_leaks,
        missing_terms=missing[:15],
    )


# ---------------------------------------------------------------------------
# 3. English Leakage
# ---------------------------------------------------------------------------

def _strip_punct(word: str) -> str:
    return word.strip(".,;:!?\"'()[]{}—-/\\|*#@%^&+=<>~`")


def _is_leakage(word: str) -> bool:
    """Return True if the word is likely an untranslated English word."""
    w = _strip_punct(word).lower()
    if not w or len(w) < 3:
        return False
    # Pure numbers / measurements
    if re.match(r'^[\d.,/\-:]+[a-z]{0,3}$', w):
        return False
    # Hex codes, part numbers, codes
    if re.match(r'^[a-z0-9]{1,2}[\-_][a-z0-9]+$', w):
        return False
    # Acronyms (2–5 uppercase letters)
    if re.match(r'^[A-Z]{2,5}$', word.strip()):
        return False
    # Must have Latin letters
    if not any('a' <= c.lower() <= 'z' for c in w):
        return False
    # Contains non-Latin scripts → not English leakage
    if any('\u0900' <= c <= '\u097F' for c in w):   # Devanagari
        return False
    if any('\u0B80' <= c <= '\u0BFF' for c in w):   # Tamil
        return False
    if any('\u0600' <= c <= '\u06FF' for c in w):   # Arabic/Jawi
        return False
    # Whitelisted technical term?
    if w in MALAY_TECH_WHITELIST or w.rstrip('s') in MALAY_TECH_WHITELIST:
        return False
    # Looks like a Malay word (prefix pattern)?
    if MALAY_PREFIXES.match(w):
        return False
    # Common Malay function word?
    if w in MALAY_FUNCTION_WORDS:
        return False

    return True


def english_leakage(translated_text: str) -> LeakageResult:
    words = translated_text.split()
    total = len(words)
    if total == 0:
        return LeakageResult(0.0, [], 0, 100.0)

    leaked = [w for w in words if _is_leakage(w)]
    unique_leaked = list(dict.fromkeys(leaked))     # deduplicated, order-preserved
    percent = round(len(leaked) / total * 100, 2)

    # Score: 100 for 0% leakage, drops linearly, floor at 0
    # Every 1% leakage = -4 points (25% leakage → 0 score)
    leakage_score = round(max(0.0, 100.0 - percent * 4), 1)

    return LeakageResult(
        leakage_percent=percent,
        leaked_words=unique_leaked[:25],
        total_words=total,
        leakage_score=leakage_score,
    )


# ---------------------------------------------------------------------------
# 4. Fluency / Malay Language Structure
# ---------------------------------------------------------------------------

def fluency_score(translated_text: str) -> FluencyResult:
    """
    Heuristic fluency score based on:
    - Malay word density (prefix patterns + function words)
    - Function-word presence (structural Malay grammar markers)
    - Sentence length distribution (too short = fragments, too long = untranslated chunks)
    """
    words = [_strip_punct(w) for w in translated_text.split() if _strip_punct(w)]
    total_words = len(words)
    sentences = split_sentences(translated_text)
    num_sents = max(len(sentences), 1)

    if total_words == 0:
        return FluencyResult(0.0, 0.0, 0.0, 0.0, 0)

    # Malay word density
    malay_count = sum(
        1 for w in words
        if w.lower() in MALAY_FUNCTION_WORDS
        or MALAY_PREFIXES.match(w.lower())
    )
    malay_density = malay_count / total_words * 100

    # Function word density
    func_count = sum(1 for w in words if w.lower() in MALAY_FUNCTION_WORDS)
    func_density = func_count / total_words * 100

    # Average sentence length
    avg_sent_len = total_words / num_sents

    # Score components
    # Malay density: ideal ~15-40%, reward proportionally, cap at 40%
    density_score = min(malay_density / 40 * 100, 100)

    # Function word density: ideal ~5-15%
    func_score = min(func_density / 12 * 100, 100)

    # Sentence length: ideal 8–25 words for technical text
    if 8 <= avg_sent_len <= 25:
        len_score = 100.0
    elif avg_sent_len < 8:
        len_score = max(0, avg_sent_len / 8 * 100)
    else:
        len_score = max(0, 100 - (avg_sent_len - 25) * 3)

    score = (density_score * 0.45 + func_score * 0.35 + len_score * 0.20)

    return FluencyResult(
        fluency_score=round(min(100.0, max(0.0, score)), 1),
        malay_word_density=round(malay_density, 1),
        function_word_density=round(func_density, 1),
        avg_sentence_length=round(avg_sent_len, 1),
        sentence_count=num_sents,
    )


# ---------------------------------------------------------------------------
# 5. Coverage Ratio
# ---------------------------------------------------------------------------

def coverage_ratio(source_text: str, translated_text: str) -> CoverageResult:
    """
    Compare word counts between source and translation.
    Malay technical text is typically 0.85–1.30× the English source length.
    """
    src_words  = len(source_text.split())
    tgt_words  = len(translated_text.split())
    ratio = tgt_words / max(src_words, 1)

    # Ideal range 0.80–1.35 → 100 points
    # Outside range: linear penalty
    if 0.80 <= ratio <= 1.35:
        score = 100.0
    elif ratio < 0.80:
        score = max(0.0, ratio / 0.80 * 100)
    else:
        score = max(0.0, 100 - (ratio - 1.35) / 0.65 * 100)

    return CoverageResult(
        coverage_score=round(score, 1),
        length_ratio=round(ratio, 3),
        source_words=src_words,
        translated_words=tgt_words,
    )


# ---------------------------------------------------------------------------
# Recommendations Engine
# ---------------------------------------------------------------------------

def _build_recommendations(
    semantic: float,
    term: TerminologyResult,
    fluency: FluencyResult,
    leak: LeakageResult,
    coverage: CoverageResult,
) -> List[str]:
    recs: List[str] = []

    if semantic < 65:
        recs.append(
            "Semantic accuracy is low — verify that meaning is preserved, "
            "especially in procedural steps and warnings."
        )
    elif semantic < 78:
        recs.append(
            "Semantic accuracy is moderate — review sentences where technical "
            "intent may be ambiguous in the target language."
        )

    if term.terminology_score < 70:
        recs.append(
            f"Terminology coverage is weak ({term.terms_found}/{term.terms_checked} terms matched). "
            "Expand the glossary or post-edit missing terms: "
            + (", ".join(term.missing_terms[:5]) or "—")
        )
    if term.wrong_script_leaks > 0:
        recs.append(
            f"{term.wrong_script_leaks} wrong-script term(s) detected "
            "(terms from another target language appearing in this translation). "
            "Check language routing in the pipeline."
        )

    if leak.leakage_percent > 20:
        recs.append(
            f"High English leakage ({leak.leakage_percent:.1f}%). "
            "Likely untranslated segments — add to MALAY_TECH_WHITELIST if intentional, "
            "or fix translation prompts. Sample: "
            + ", ".join(leak.leaked_words[:8])
        )
    elif leak.leakage_percent > 10:
        recs.append(
            f"Moderate English leakage ({leak.leakage_percent:.1f}%). "
            "Check whether flagged words are whitelisted loanwords or genuine misses."
        )

    if fluency.malay_word_density < 8:
        recs.append(
            "Very low Malay word density — the translation may contain large untranslated blocks."
        )
    if fluency.avg_sentence_length > 30:
        recs.append(
            f"Average sentence length is long ({fluency.avg_sentence_length:.0f} words). "
            "Consider splitting complex sentences for readability."
        )
    if fluency.avg_sentence_length < 5:
        recs.append(
            "Very short average sentence length — check for incomplete or fragmented translations."
        )

    if coverage.length_ratio < 0.70:
        recs.append(
            f"Translation appears significantly shorter than source (ratio {coverage.length_ratio:.2f}). "
            "Content may have been omitted."
        )
    elif coverage.length_ratio > 1.60:
        recs.append(
            f"Translation is much longer than source (ratio {coverage.length_ratio:.2f}). "
            "Check for repetition, hallucination, or verbose phrasing."
        )

    if not recs:
        recs.append("Translation quality is satisfactory. Continue monitoring terminology and leakage.")

    return recs


# ---------------------------------------------------------------------------
# Main Evaluation Function
# ---------------------------------------------------------------------------

def evaluate_translation(
    source_text: Union[str, Path],
    translated_text: Union[str, Path],
    glossary: Dict[str, Dict[str, str]],
    target_lang: str = "Malay",
) -> EvaluationReport:
    """
    Full reference-free evaluation pipeline.

    Parameters
    ----------
    source_text     : Path to English XML or raw text string.
    translated_text : Path to translated XML or raw text string.
    glossary        : {source_term: {lang_code: translated_term}} mapping.
    target_lang     : Target language name (used for display and lang-code resolution).

    Returns
    -------
    EvaluationReport dataclass with .summary() and .to_dict() helpers.
    """
    # Resolve language code
    tl = target_lang.lower()
    lang_code = (
        "ms" if any(x in tl for x in ("malay", "ms", "bahasa melayu", "bm")) else
        "hi" if "hindi" in tl else
        "ta" if "tamil" in tl else
        "ms"   # default to Malay
    )

    log.info("Extracting text from source …")
    src_clean   = extract_text_from_xml(source_text)
    log.info("Extracting text from translation …")
    trans_clean = extract_text_from_xml(translated_text)

    log.info("Running semantic accuracy …")
    sem_score = semantic_accuracy(src_clean, trans_clean)

    log.info("Running terminology quality …")
    term_result = terminology_quality(trans_clean, glossary, lang_code)

    log.info("Running English leakage …")
    leak_result = english_leakage(trans_clean)

    log.info("Running fluency analysis …")
    flu_result = fluency_score(trans_clean)

    log.info("Running coverage ratio …")
    cov_result = coverage_ratio(src_clean, trans_clean)

    # --- Weighted overall score ---
    overall = (
        sem_score                        * WEIGHTS["semantic"]   +
        term_result.terminology_score    * WEIGHTS["terminology"] +
        flu_result.fluency_score         * WEIGHTS["fluency"]    +
        leak_result.leakage_score        * WEIGHTS["leakage"]    +
        cov_result.coverage_score        * WEIGHTS["coverage"]
    )
    overall = round(min(100.0, max(0.0, overall)), 1)

    # Rating
    rating = next(label for threshold, label in RATING_THRESHOLDS if overall >= threshold)

    # Recommendations
    recs = _build_recommendations(sem_score, term_result, flu_result, leak_result, cov_result)

    return EvaluationReport(
        overall_score=overall,
        rating=rating,
        target_lang=target_lang,
        semantic_accuracy=sem_score,
        terminology=term_result,
        fluency=flu_result,
        leakage=leak_result,
        coverage=cov_result,
        recommendations=recs,
    )


# ---------------------------------------------------------------------------
# Batch Evaluation
# ---------------------------------------------------------------------------

def evaluate_batch(
    pairs: List[Tuple[Union[str, Path], Union[str, Path]]],
    glossary: Dict[str, Dict[str, str]],
    target_lang: str = "Malay",
) -> List[EvaluationReport]:
    """
    Evaluate multiple source/translation pairs.

    Parameters
    ----------
    pairs : List of (source_path, translated_path) tuples.

    Returns
    -------
    List of EvaluationReport objects.
    """
    reports = []
    for i, (src, tgt) in enumerate(pairs, 1):
        log.info("─── Evaluating pair %d/%d ───", i, len(pairs))
        report = evaluate_translation(src, tgt, glossary, target_lang)
        reports.append(report)
        print(report.summary())
    return reports


# ---------------------------------------------------------------------------
# Standalone Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    import sys

    print("=== Automotive Translation Quality Evaluator (English → Malay) ===\n")

    # ── Paths (edit these) ──────────────────────────────────────────────────
    SOURCE_XML     = "english.xml"
    TRANSLATED_XML = "malay.xml"
    GLOSSARY_PATH  = "upg.json"
    TARGET_LANG    = "Malay"
    # ────────────────────────────────────────────────────────────────────────

    # Load glossary
    try:
        with open(GLOSSARY_PATH, "r", encoding="utf-8") as f:
            glossary = json.load(f)
        log.info("Loaded %d glossary entries from %s", len(glossary), GLOSSARY_PATH)
    except FileNotFoundError:
        log.warning("Glossary not found at %s — terminology score will be 80.0 (default).", GLOSSARY_PATH)
        glossary = {}
    except json.JSONDecodeError as e:
        log.error("Failed to parse glossary JSON: %s", e)
        sys.exit(1)

    # Run evaluation
    try:
        report = evaluate_translation(SOURCE_XML, TRANSLATED_XML, glossary, TARGET_LANG)
        print(report.summary())

        # Optionally dump full JSON report
        out_path = Path("evaluation_report.json")
        out_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("Full report saved to %s", out_path)

    except FileNotFoundError as e:
        log.error("File not found: %s", e)
        sys.exit(1)
    except Exception as e:
        log.error("Evaluation failed: %s", e)
        import traceback
        traceback.print_exc()
        sys.exit(1)