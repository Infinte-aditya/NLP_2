from typing import List
# Import our new IndicTrans2 wrapper
from backend.pipeline.indic_model import translate_batch

def translate_sentences(sentences: List[str], target_lang: str, fast_mode: bool = False) -> List[str]:
    """
    Translates a list of sentences using IndicTrans2.
    target_lang: 'Tamil' or 'Hindi' or 'ta'/'hi'
    fast_mode: if True, use faster generation settings (fewer beams).
    """
    # Map to FLORES-200 codes for IndicTrans2
    # Tamil: tam_Taml
    # Hindi: hin_Deva
    
    code_map = {
        'tamil': 'tam_Taml',
        'ta': 'tam_Taml',
        'hindi': 'hin_Deva',
        'hi': 'hin_Deva'
    }
    
    key = target_lang.lower()
    target_code = code_map.get(key, 'tam_Taml') # Default to Tamil
    
    # Check if key not found but contains 'hindi' or 'tamil'
    if key not in code_map:
        if 'hindi' in key: target_code = 'hin_Deva'
        elif 'tamil' in key: target_code = 'tam_Taml'
    
    return translate_batch(sentences, target_code, fast_mode=fast_mode)
