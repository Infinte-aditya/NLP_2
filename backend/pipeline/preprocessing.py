import json
import re
import nltk
from typing import Dict, List, Tuple

# Download nltk data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt')
    nltk.download('punkt_tab')

def load_glossary(path: str) -> Dict[str, Dict[str, str]]:
    """Loads the multilingual glossary from a JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        glossary = json.load(f)
    return glossary

def classify_terms(glossary: Dict[str, Dict[str, str]], target_lang: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    protected = {}
    
    target_lower = target_lang.lower()
    if any(x in target_lower for x in ('malay', 'ms', 'bahasa')):
        lang_code = 'ms'
    elif 'hindi' in target_lower or target_lower == 'hi':
        lang_code = 'hi'
    else:
        lang_code = 'ta'

    for term, translations in glossary.items():
        if lang_code not in translations:
            continue
            
        trans_value = translations[lang_code]
        
        # NEW: For Malay we want the English term itself
        if lang_code == 'ms' and trans_value == term:
            protected[term] = term          # protect original English
        else:
            protected[term] = trans_value

    return protected, {}

def segment_text(text: str) -> List[str]:
    """Segments text into sentences using NLTK."""
    return nltk.sent_tokenize(text)

def protect_terms(text: str, protected_glossary: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
    """
    Masks ONLY terms in the protected_glossary.
    Returns: (masked_text, placeholder_map)
    """
    # Sort by length desc for longest match
    sorted_terms = sorted(protected_glossary.keys(), key=len, reverse=True)
    
    placeholder_map = {}
    protected_text = text
    counter = 0
    
    # 1. Protect Technical Codes & Units (Alphanumeric, units, dimensions)
    # Examples: 1E-3, INOMOA150001-03, (A): 09915M47341, 35 N-m, 100 mm, 2 cm, 14.5 psi
    # This prevents the model from attempting to translate or mangle technical IDs.
    code_pattern = re.compile(r'\b(?:[A-Z0-9]{2,}[-:][A-Z0-9-]+|[A-Z]{1,2}\d{3,}[A-Z0-9]*|[0-9][A-Z]-\d|\d+(?:\.\d+)?\s*(?:mm|cm|m|km|N-m|psi|kgf-cm|ft-lb|in-lb|Pa|kPa|bar|L|mL|V|A|W|Hz))\b')
    
    def repl_code(match):
        nonlocal counter
        code = match.group(0).strip()
        placeholder = f"__TERM_{counter}__"
        placeholder_map[placeholder] = code
        counter += 1
        # Removing forced spaces around placeholder to prevent "_" connectors from model
        return placeholder

    protected_text = code_pattern.sub(repl_code, protected_text)

    # 2. Protect Glossary Terms
    for term in sorted_terms:
        # Match whole words only, but allow for common plural 's' optionally if not in glossary
        # This handles "Journal" when "Journals" is in glossary, and vice versa.
        # We also check for the term itself.
        
        # Pattern 1: The exact term
        pattern_exact = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
        
        # Pattern 2: If term ends in 's', try singular too. If not, try plural.
        alt_term = None
        if term.lower().endswith('s'):
            alt_term = term[:-1]
        else:
            alt_term = term + 's'
            
        pattern_alt = re.compile(r'\b' + re.escape(alt_term) + r'\b', re.IGNORECASE) if alt_term else None

        for pattern in [pattern_exact, pattern_alt]:
            if not pattern: continue
            
            while True:
                match = pattern.search(protected_text)
                if not match: break
                
                placeholder = f"__TERM_{counter}__"
                # We map placeholder -> ORIGINAL translated term value from the glossary entry of the root term
                placeholder_map[placeholder] = protected_glossary[term]
                
                # Replace the match with the placeholder
                start, end = match.span()
                protected_text = protected_text[:start] + placeholder + protected_text[end:]
                counter += 1
            
    return protected_text, placeholder_map
