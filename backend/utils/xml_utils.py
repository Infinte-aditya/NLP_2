"""
XML Translation Utility
-----------------------
Parses an XML file, extracts all human-readable text nodes,
sends them through the translation pipeline (with glossary
protection), and writes the translated text back into the
same XML structure — preserving tags, attributes, and hierarchy.

Performance: non-translatable segments (pure numbers, codes,
single characters) are detected and skipped entirely.
"""

import re
import xml.etree.ElementTree as ET
from typing import Callable, List, Optional

# Matches segments that are purely punctuation / numbers / symbols
_SKIP_PATTERN = re.compile(
    r'^[\d\s\.\-\:\,\;\(\)\[\]\{\}\/\\#\*\+\=\<\>\&\@\!\?\%\$\^\~\`\'\"]+$'
)


def _is_translatable(text: str) -> bool:
    """Return False for text that should NOT be sent to the engine."""
    stripped = text.strip()
    if not stripped:
        return False
    if len(stripped) <= 1:
        return False
    if _SKIP_PATTERN.match(stripped):
        return False
    # If every character is ASCII and no alphabetic chars → skip
    if stripped.isascii() and not any(c.isalpha() for c in stripped):
        return False
    return True


def translate_xml(
    input_path: str,
    output_path: str,
    translation_helper: Callable,
    target_lang: str,
    progress_callback: Optional[Callable] = None,
):
    """
    Translate all text content inside an XML file while
    preserving the document structure (tags, attributes, nesting).
    """

    if progress_callback:
        progress_callback("Loading XML document...", 10)

    # ── 1. Parse ──────────────────────────────────────────────
    tree = ET.parse(input_path)
    root = tree.getroot()

    # ── 2. Collect text segments ──────────────────────────────
    segments: list[tuple[ET.Element, str]] = []   # (element, "text"|"tail")
    texts: list[str] = []

    def _walk(elem: ET.Element):
        if elem.text and elem.text.strip():
            segments.append((elem, "text"))
            texts.append(elem.text)
        for child in elem:
            _walk(child)
            if child.tail and child.tail.strip():
                segments.append((child, "tail"))
                texts.append(child.tail)

    _walk(root)

    if not texts:
        tree.write(output_path, encoding="unicode", xml_declaration=True)
        if progress_callback:
            progress_callback("No translatable text found.", 100)
        return

    # ── 3. Filter non-translatable segments ───────────────────
    translatable_indices: List[int] = []
    translatable_texts: List[str] = []
    for i, t in enumerate(texts):
        if _is_translatable(t):
            translatable_indices.append(i)
            translatable_texts.append(t)

    skipped = len(texts) - len(translatable_texts)
    if progress_callback:
        progress_callback(
            f"Found {len(texts)} nodes, {skipped} skipped (non-text). "
            f"Translating {len(translatable_texts)} segments...",
            15,
        )

    if not translatable_texts:
        tree.write(output_path, encoding="unicode", xml_declaration=True)
        if progress_callback:
            progress_callback("Nothing to translate after filtering.", 100)
        return

    # ── 4. Translate via the shared pipeline ──────────────────
    if progress_callback:
        progress_callback(
            f"Translating {len(translatable_texts)} segments...", 20
        )

    translated_texts = translation_helper(
        translatable_texts, target_lang, progress_callback
    )

    # ── 5. Write translated text back into the tree ───────────
    if progress_callback:
        progress_callback("Reconstructing XML structure...", 85)

    # Build a full-size result array aligned with the original `texts` list
    full_results = list(texts)  # start with originals (keeps skipped segments)
    for j, orig_idx in enumerate(translatable_indices):
        if j < len(translated_texts) and translated_texts[j]:
            full_results[orig_idx] = translated_texts[j]

    for i, (elem, attr) in enumerate(segments):
        if i >= len(full_results):
            break
        translated = full_results[i]
        if not translated:
            continue

        original = getattr(elem, attr)
        # Preserve leading / trailing whitespace from the original
        leading_ws = ""
        trailing_ws = ""
        if original:
            stripped = original.lstrip()
            leading_ws = original[: len(original) - len(stripped)]
            stripped2 = original.rstrip()
            trailing_ws = original[len(stripped2):]

        setattr(elem, attr, leading_ws + translated.strip() + trailing_ws)

    # ── 6. Save ───────────────────────────────────────────────
    if progress_callback:
        progress_callback("Saving translated XML...", 95)

    tree.write(output_path, encoding="unicode", xml_declaration=True)

    if progress_callback:
        progress_callback("XML translation complete.", 100)
