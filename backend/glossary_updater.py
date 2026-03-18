import re
import json
import os
from collections import Counter
from typing import Dict, List, Tuple

# ── Optional dependency ───────────────────────────────────────────────────────
try:
    from indic_transliteration import sanscript
    from indic_transliteration.transliterate import transliterate as _transliterate
    HAS_INDIC_TRANSLIT = True
except ImportError:
    HAS_INDIC_TRANSLIT = False
    print("[GlossaryUpdater] indic-transliteration not found. "
          "Using phonetic fallback. Run: pip install indic-transliteration")

# ── Words NLLB handles fine — never auto-add ──────────────────────────────────
STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "it", "its", "this", "that", "these", "those", "not",
    "no", "yes", "if", "as", "so", "do", "did", "has", "have", "had",
    "will", "would", "can", "could", "should", "may", "might", "must",
    "shall", "when", "where", "which", "who", "how", "what", "then",
    "than", "also", "only", "just", "more", "after", "before", "during",
    "remove", "install", "check", "use", "note", "see", "refer", "ensure",
    "make", "take", "set", "get", "put", "keep", "hold", "turn", "pull",
    "push", "open", "close", "apply", "clean", "allow", "start", "stop",
    "while", "until", "each", "all", "both", "any", "some", "into",
    "over", "under", "through", "between", "above", "below", "without",
    "within", "along", "around", "near", "side", "back", "front", "top",
    "bottom", "left", "right", "upper", "lower", "inner", "outer", "main",
    "new", "old", "high", "low", "long", "short", "large", "small",
    "type", "part", "area", "end", "case", "line", "point", "level",
    "order", "number", "step", "time", "way", "place", "position",
    "following", "below", "above", "shown", "figure", "table", "section",
    "page", "item", "list", "refer", "shown", "used", "using", "when",
        "damage", "power", "safe", "value", "road", "condition", "signal",
    "light", "door", "hill", "even", "mode", "range", "status", "view",
    "complete", "lever", "reading", "running", "engaged", "request",
    "supply", "warning", "error", "limit", "progress", "self", "tune",
    "disc", "ring", "guide", "specified", "learning", "feedback",
    "connection", "operating", "regulations", "permissible", "approx",
    "visual", "hard", "generic", "trouble", "driver", "drivers",
    "diagram", "procedure", "confirmation", "revolution", "shifting",
    "overspeed", "cranking", "depressing", "synchronizer", "sleeve",
    "ignition", "indicator", "operation", "performance"
}

def _is_valid_term(word: str) -> bool:
    """
    Filter out model artifacts and common words before adding to glossary.
    """
    # Too short
    if len(word) < 5:
        return False
    # Contains digits — likely a code fragment
    if any(c.isdigit() for c in word):
        return False
    # Looks like a concatenation artifact (camelCase or two words joined)
    # e.g. 'wiignition', 'frondoor', 'Noignition', 'morevalue'
    if re.search(r'[a-z][A-Z]', word):   # camelCase
        return False
    # Repeated letters (model artifact like 'Driverss')
    if re.search(r'(.)\1{2,}', word):
        return False
    # Contains known bad patterns — prefix concatenations
    bad_prefixes = ['wi', 'no', 'dc', 'se', 'ad', 'sl', 'fr']
    if len(word) > 6 and word.lower()[:2] in bad_prefixes:
        # Check if remainder is a known word (e.g. 'no' + 'ignition')
        for bp in bad_prefixes:
            if word.lower().startswith(bp) and word.lower()[len(bp):] in STOPWORDS:
                return False
    return True

CODE_PATTERN = re.compile(
    r'\b(?:[A-Z]{1,3}\d{2,}[A-Z0-9]*|[A-Z0-9]{2,}-[A-Z0-9-]+|\d+[A-Z]{2,}\d*)\b'
)

ENGLISH_SURVIVOR_PATTERN = re.compile(r'\b[A-Za-z][a-z]{2,}\b')

# ── Phonetic mapping for transliteration ─────────────────────────────────────
_PHONETIC_MAP = [
    ("tion", "shana"), ("sion", "shana"), ("ck",   "k"),
    ("ph",   "f"),     ("th",   "th"),    ("sh",   "sh"),
    ("ch",   "ch"),    ("gh",   "g"),     ("wh",   "w"),
    ("ee",   "ii"),    ("oo",   "uu"),    ("ing",  "ing"),
    ("ture", "char"),  ("ure",  "ar"),    ("age",  "ej"),
    ("ive",  "iv"),    ("ble",  "bal"),   ("ple",  "pal"),
    ("ic",   "ik"),    ("al",   "al"),    ("er",   "ar"),
    ("or",   "or"),    ("ar",   "ar"),    ("ly",   "lii"),
]

def _to_itrans(word: str) -> str:
    result = word.lower()
    for eng, itr in _PHONETIC_MAP:
        result = result.replace(eng, itr)
    return result

def transliterate_word(word: str, script: str) -> str:
    """Transliterate English word to Devanagari (hi) or Tamil (ta)."""
    if HAS_INDIC_TRANSLIT:
        try:
            target = sanscript.DEVANAGARI if script == "hi" else sanscript.TAMIL
            # Try direct IAST first — works better for English loanwords
            result = _transliterate(word.lower(), sanscript.IAST, target)
            if result and result != word.lower() and not result.isascii():
                return result
        except Exception:
            pass
    return word  # fallback: keep English

def get_both_transliterations(word: str) -> Dict[str, str]:
    return {
        "hi": transliterate_word(word, "hi"),
        "ta": transliterate_word(word, "ta"),
    }

# ── Frequency Tracker ─────────────────────────────────────────────────────────
class FrequencyTracker:
    def __init__(self, path: str):
        self.path = path
        self.counts: Counter = self._load()

    def _load(self) -> Counter:
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                return Counter(json.load(f))
        return Counter()

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(dict(self.counts), f, ensure_ascii=False, indent=2)

    def increment(self, words: List[str]) -> Dict[str, int]:
        for w in words:
            self.counts[w.lower()] += 1
        self._save()
        return {w.lower(): self.counts[w.lower()] for w in words}

# ── GlossaryUpdater ───────────────────────────────────────────────────────────
class GlossaryUpdater:
    THRESHOLD = 2

    def __init__(self, glossary_path: str, counter_path: str = None):
        self.glossary_path = glossary_path
        self.counter_path = counter_path or glossary_path.replace(
            ".json", "_freq_counter.json"
        )
        self.tracker = FrequencyTracker(self.counter_path)
        self.glossary = self._load_glossary()

    def _load_glossary(self) -> Dict:
        with open(self.glossary_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_glossary(self):
        with open(self.glossary_path, "w", encoding="utf-8") as f:
            json.dump(self.glossary, f, ensure_ascii=False, indent=2)

    def _already_in_glossary(self, word: str) -> bool:
        return word in self.glossary or word.lower() in self.glossary

    def _detect_survivors(self, text: str) -> List[str]:
        candidates = ENGLISH_SURVIVOR_PATTERN.findall(text)
        survivors = []
        for word in candidates:
            if word.lower() in STOPWORDS:
                continue
            if CODE_PATTERN.match(word):
                continue
            if len(word) < 4:
                continue
            if word.isupper():
                continue
            if self._already_in_glossary(word):
                continue
            survivors.append(word)
        return list(set(survivors))

    def process(
        self,
        translated_text: str,
        tgt_script: str = "hi"
    ) -> Tuple[str, List[str]]:
        """
        Call after restore_placeholders() for every translated segment.
        Returns (cleaned_text, list_of_newly_added_terms)
        """
        survivors = self._detect_survivors(translated_text)
        if not survivors:
            return translated_text, []

        counts = self.tracker.increment(survivors)
        newly_added = []
        result_text = translated_text

        for word in survivors:
            if not _is_valid_term(word):
                continue
            translit = get_both_transliterations(word)
            replacement = translit[tgt_script]

            # Replace in text immediately
            result_text = re.sub(
                r'\b' + re.escape(word) + r'\b',
                replacement,
                result_text,
                flags=re.IGNORECASE
            )

            # Add to glossary if seen enough times
            if counts[word.lower()] >= self.THRESHOLD:
                self.glossary[word] = translit
                newly_added.append(word)
                print(
                    f"[GlossaryUpdater] '{word}' seen {counts[word.lower()]}x "
                    f"→ added | hi: {translit['hi']} | ta: {translit['ta']}"
                )

        if newly_added:
            self._save_glossary()

        return result_text, newly_added

    def get_pending_terms(self) -> Dict[str, int]:
        """Words seen at least once but not yet at threshold — useful for review."""
        return {
            word: count
            for word, count in self.tracker.counts.items()
            if count < self.THRESHOLD and not self._already_in_glossary(word)
        }