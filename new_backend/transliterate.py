"""
transliterate_glossary.py
=========================
Reads a JSONL automotive glossary, runs each term through the
Microsoft Azure Translator **Transliteration** endpoint, and writes
a structured JSON glossary keyed by the canonical English term.

Input  (JSONL)  — one JSON object per line:
    {"term": ["3-2 Timing Solenoid", "3-2 Timing Solenoid", "3-2TS"]}

Output (JSON):
    {
      "3-2 Timing Solenoid": {
        "en":      "3-2 Timing Solenoid",
        "aliases": ["3-2 Timing Solenoid", "3-2TS"],
        "ta":      "3-2 டைமிங் சோலனாய்ட்",
        "hi":      "3-2 टाइमिंग सोलेनॉइड",
        "ms_jawi": "3-2 تيميڠ سولينويد"
      },
      ...
    }

Language / Script map used
--------------------------
  ta  → Tamil   : English Latin  →  Tamil script  (Taml)
  hi  → Hindi   : English Latin  →  Devanagari    (Deva)
  ms  → Malay   : English Latin  →  Jawi / Arabic (Arab)   [optional]

Note: Standard Malay uses Latin script, so transliteration produces
Jawi.  If you want Rumi (Latin) Malay *translation* instead, flip the
USE_JAWI_FOR_MALAY flag to False and the script will call the
/translate endpoint for `ms` only.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import requests

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Azure Configuration  ← edit these
# ---------------------------------------------------------------------------

AZURE_KEY    = ""
AZURE_REGION = ""
BASE_URL     = ""

# Set to True  → Malay output will be in Jawi (Arabic script)
# Set to False → Malay output will be translated Latin Rumi (calls /translate)
USE_JAWI_FOR_MALAY = False


# ---------------------------------------------------------------------------
# Script / Language Configuration
# ---------------------------------------------------------------------------

# Each entry:  lang_code → (azure_language, from_script, to_script)
# These are passed directly to the /transliterate endpoint params.
TRANSLITERATE_LANGS: Dict[str, tuple] = {
    "ta":      ("ta", "Latn", "Taml"),   # Tamil script
    "hi":      ("hi", "Latn", "Deva"),
    "ml": ("ml", "Latn", "Mlym"),  # Malayalam
    "bn": ("bn", "Latn", "Beng"),  # Bengali (already correct)
    "pa": ("pa", "Latn", "Guru"),  # Punjabi (Gurmukhi)
    "gu": ("gu", "Latn", "Gujr"),  # Gujarati
    "or": ("or", "Latn", "Orya"),  # Odia
    # "mr": ("mr", "Latn", "Deva"),  # Marathi (Devanagari)
    "ja": ("ja", "Latn", "Jpan"),  # Japanese 
    }

# Malay gets its own handling based on USE_JAWI_FOR_MALAY
# MALAY_TRANSLITERATE = ("ms", "Latn", "Arab")   # Jawi
# MALAY_TRANSLATE_TO  = "ms"                      # Rumi via /translate


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _base_headers() -> Dict[str, str]:
    return {
        "Ocp-Apim-Subscription-Key":    AZURE_KEY,
        "Ocp-Apim-Subscription-Region": AZURE_REGION,
        "Content-Type":                 "application/json",
        "X-ClientTraceId":              str(uuid.uuid4()),
    }


def _post_with_retry(
    url: str,
    params: Dict,
    body: List[Dict],
    retries: int = 3,
    backoff: float = 2.0,
) -> Optional[List[Dict]]:
    """POST to Azure with simple exponential back-off on 429 / 5xx."""
    for attempt in range(1, retries + 1):
        try:
            r = requests.post(
                url,
                params=params,
                headers=_base_headers(),
                json=body,
                timeout=30,
            )
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                wait = backoff ** attempt
                log.warning("Rate-limited (429). Waiting %.1fs before retry %d/%d …", wait, attempt, retries)
                time.sleep(wait)
                continue
            log.error("HTTP %d: %s", r.status_code, r.text[:300])
            return None
        except requests.RequestException as exc:
            log.error("Request error (attempt %d/%d): %s", attempt, retries, exc)
            if attempt < retries:
                time.sleep(backoff * attempt)
    return None


# ---------------------------------------------------------------------------
# Transliteration
# ---------------------------------------------------------------------------

def transliterate_batch(
    texts: List[str],
    azure_language: str,
    from_script: str,
    to_script: str,
    batch_size: int = 25,
) -> List[str]:
    """
    Transliterate a list of strings using the Azure /transliterate endpoint.
    Returns a list of transliterated strings in the same order.
    Falls back to the original text on error.
    """
    results: List[str] = list(texts)   # start as copy of originals (safe fallback)

    for i in range(0, len(texts), batch_size):
        chunk     = texts[i : i + batch_size]
        body      = [{"text": t} for t in chunk]
        params    = {
            "api-version": "3.0",
            "language":    azure_language,
            "fromScript":  from_script,
            "toScript":    to_script,
        }

        log.info(
            "  Transliterating %d terms → %s (%s→%s) [batch %d]",
            len(chunk), azure_language, from_script, to_script, i // batch_size + 1,
        )

        data = _post_with_retry(BASE_URL + "transliterate", params, body)
        if data is None:
            log.warning("  Batch failed — keeping originals for this chunk.")
            continue

        for j, item in enumerate(data):
            results[i + j] = item.get("text", chunk[j])

        time.sleep(0.1)   # small courtesy delay between batches

    return results


# ---------------------------------------------------------------------------
# Translation (used for Rumi Malay only)
# ---------------------------------------------------------------------------

def translate_batch(
    texts: List[str],
    to_lang: str,
    from_lang: str = "en",
    batch_size: int = 25,
) -> List[str]:
    """
    Translate a list of strings using the Azure /translate endpoint.
    Returns translated strings in the same order.
    """
    results: List[str] = list(texts)

    for i in range(0, len(texts), batch_size):
        chunk  = texts[i : i + batch_size]
        body   = [{"text": t} for t in chunk]
        params = {
            "api-version": "3.0",
            "from":        from_lang,
            "to":          to_lang,
        }

        log.info(
            "  Translating %d terms → %s [batch %d]",
            len(chunk), to_lang, i // batch_size + 1,
        )

        data = _post_with_retry(BASE_URL + "translate", params, body)
        if data is None:
            log.warning("  Batch failed — keeping originals for this chunk.")
            continue

        for j, item in enumerate(data):
            try:
                results[i + j] = item["translations"][0]["text"]
            except (KeyError, IndexError):
                pass   # fallback to original already set

        time.sleep(0.1)

    return results


# ---------------------------------------------------------------------------
# JSONL Reader
# ---------------------------------------------------------------------------

def load_jsonl(path: str | Path) -> List[Dict]:
    records = []
    with Path(path).open(encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
                terms = obj.get("term", [])
                if not terms:
                    continue
                records.append({
                    "canonical": terms[0].strip(),   # ← only first term sent to API
                    "aliases":   [t.strip() for t in terms[1:]]
                })
            except json.JSONDecodeError as exc:
                log.warning("Line %d skipped: %s", lineno, exc)
    return records

# ---------------------------------------------------------------------------
# Main Build Function
# ---------------------------------------------------------------------------

def build_glossary(
    input_jsonl:  str | Path,
    output_json:  str | Path,
    batch_size:   int = 25,
) -> Dict:
    """
    Read the JSONL glossary, transliterate every canonical English term
    into all configured languages, and write the enriched JSON glossary.

    Output structure per entry
    --------------------------
    {
      "<canonical English term>": {
        "en":      "<canonical term>",
        "aliases": ["<variant1>", "<variant2>"],   # remaining items in term[]
        "ta":      "<Tamil script>",
        "hi":      "<Devanagari>",
        "ms":      "<Jawi or Rumi Malay>"           # key depends on USE_JAWI_FOR_MALAY
      }
    }
    """
    records = load_jsonl(input_jsonl)

    # Deduplicate by canonical term, merge aliases
    glossary = {}
    for rec in records:
        key = rec["canonical"]
        if key in glossary:
            glossary[key]["aliases"] = sorted(
                set(glossary[key]["aliases"]) | set(rec["aliases"])
            )
            continue
        glossary[key] = {"en": key, "aliases": rec["aliases"]}

    # Only the canonical (first) term goes to the API
    canonical_terms = list(glossary.keys())

    for lang_code, (azure_lang, from_sc, to_sc) in TRANSLITERATE_LANGS.items():
        results = transliterate_batch(canonical_terms, azure_lang, from_sc, to_sc, batch_size)
        for term, result in zip(canonical_terms, results):
            glossary[term][lang_code] = result

    # # ── Malay: Jawi transliteration OR Rumi translation ───────────────────
    # log.info("── Language: MS (%s) ────────────────────────────────",
    #          "Jawi" if USE_JAWI_FOR_MALAY else "Rumi/Latin")

    # if USE_JAWI_FOR_MALAY:
    #     ms_key = "ms_jawi"
    #     # az_lang, from_sc, to_sc = MALAY_TRANSLITERATE
    #     malay_results = transliterate_batch(
    #         canonical_terms, az_lang, from_sc, to_sc, batch_size
    #     )
    # else:
    #     ms_key = "ms"
    #     malay_results = translate_batch(canonical_terms, MALAY_TRANSLATE_TO, batch_size=batch_size)

    # for term, result in zip(canonical_terms, malay_results):
    #     glossary[term][ms_key] = result
    

    for term, result in (canonical_terms):
        glossary[term] = result

    # ── Write output ───────────────────────────────────────────────────────
    out = Path(output_json)
    out.write_text(json.dumps(glossary, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Glossary saved → %s  (%d entries)", out, len(glossary))

    # Print a few sample entries for quick verification
    _print_sample(glossary, n=3)

    return glossary


# ---------------------------------------------------------------------------
# Sample Preview
# ---------------------------------------------------------------------------

def _print_sample(glossary: Dict, n: int = 3) -> None:
    print(f"\n{'─'*60}")
    print(f"  Sample output ({min(n, len(glossary))} of {len(glossary)} entries)")
    print(f"{'─'*60}")
    for i, (key, val) in enumerate(glossary.items()):
        if i >= n:
            break
        print(f"\n  EN : {val['en']}")
        if val.get("aliases"):
            print(f"  ALT: {', '.join(val['aliases'])}")
        for code in ("ta", "hi", "ms", "ms_jawi"):
            if code in val:
                label = {"ta": "TA", "hi": "HI", "ms": "MS (Rumi)", "ms_jawi": "MS (Jawi)"}[code]
                print(f"  {label}: {val[code]}")
    print(f"\n{'─'*60}\n")


# ---------------------------------------------------------------------------
# Incremental / Resume Support
# ---------------------------------------------------------------------------

def build_glossary_incremental(
    input_jsonl:  str | Path,
    output_json:  str | Path,
    batch_size:   int = 25,
) -> Dict:
    """
    Same as build_glossary() but resumes from a partially-written output file.
    Useful for large glossaries if the run is interrupted mid-way.

    Only terms missing at least one language key are re-processed.
    """
    out = Path(output_json)
    existing: Dict = {}

    if out.exists():
        try:
            existing = json.loads(out.read_text(encoding="utf-8"))
            log.info("Resuming: loaded %d existing entries from %s", len(existing), out.name)
        except json.JSONDecodeError:
            log.warning("Could not parse existing output — starting fresh.")

    # Determine which lang keys we expect
    expected_keys = set(TRANSLITERATE_LANGS.keys())
    expected_keys.add("ms_jawi" if USE_JAWI_FOR_MALAY else "ms")

    records = load_jsonl(input_jsonl)
    needs_work: List[str] = []

    for rec in records:
        terms     = rec.get("term", [])
        canonical = terms[0].strip() if terms else None
        if not canonical:
            continue
        entry = existing.get(canonical, {})
        if not expected_keys.issubset(entry.keys()):
            needs_work.append(canonical)

    if not needs_work:
        log.info("All entries already processed. Nothing to do.")
        return existing

    log.info("%d terms need processing (out of %d total).", len(needs_work), len(records))

    # Build subset glossary for only missing terms
    for term in needs_work:
        if term not in existing:
            existing[term] = {"en": term, "aliases": []}

    # Transliterate non-Malay langs
    for lang_code, (azure_lang, from_sc, to_sc) in TRANSLITERATE_LANGS.items():
        missing_for_lang = [t for t in needs_work if lang_code not in existing.get(t, {})]
        if not missing_for_lang:
            continue
        log.info("── %s: %d terms to process ──", lang_code.upper(), len(missing_for_lang))
        results = transliterate_batch(missing_for_lang, azure_lang, from_sc, to_sc, batch_size)
        for term, result in zip(missing_for_lang, results):
            existing[term][lang_code] = result

    # # Malay
    # ms_key = "ms_jawi" if USE_JAWI_FOR_MALAY else "ms"
    # missing_ms = [t for t in needs_work if ms_key not in existing.get(t, {})]
    # if missing_ms:
    #     log.info("── MS: %d terms to process ──", len(missing_ms))
    #     if USE_JAWI_FOR_MALAY:
    #         az_lang, from_sc, to_sc = MALAY_TRANSLITERATE
    #         results = transliterate_batch(missing_ms, az_lang, from_sc, to_sc, batch_size)
    #     else:
    #         results = translate_batch(missing_ms, MALAY_TRANSLATE_TO, batch_size=batch_size)
    #     for term, result in zip(missing_ms, results):
    #         existing[term][ms_key] = result

    # Save
    out.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Saved %d entries → %s", len(existing), out)
    _print_sample(existing, n=3)

    return existing


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    INPUT_JSONL  = "new_glossary.jsonl"      # ← your input file
    OUTPUT_JSON  = "new_transliterated_glossary.json"

    # Use build_glossary() for a clean run
    # Use build_glossary_incremental() to resume after interruption
    build_glossary_incremental(INPUT_JSONL, OUTPUT_JSON, batch_size=25)