from typing import List
# Import our new IndicTrans2 wrapper
from backend.pipeline.indic_model import translate_batch

def translate_sentences(sentences: List[str], target_lang: str, fast_mode: bool = False, num_beams: int = None) -> List[str]:
    """
    Translates a list of sentences using IndicTrans2.
    target_lang: 'Tamil' or 'Hindi' or 'ta'/'hi'
    fast_mode: if True, use faster generation settings (fewer beams).
    """
    # Map to FLORES-200 codes for IndicTrans2
    # Tamil: tam_Taml
    # Hindi: hin_Deva
    
    code_map = {
        'tamil':  'tam_Taml',
        'ta':     'tam_Taml',
        'hindi':  'hin_Deva',
        'hi':     'hin_Deva',
        'malay':  'zsm_Latn',
        'ms':     'zsm_Latn',
        'bahasa': 'zsm_Latn',
    }

    key = target_lang.lower()

    # Check contains — handles "Bahasa Malaysia", "Bahasa Melayu" etc.
    if 'malay' in key or 'bahasa' in key or key == 'ms':
        target_code = 'zsm_Latn'
    elif 'hindi' in key:
        target_code = 'hin_Deva'
    elif 'tamil' in key:
        target_code = 'tam_Taml'
    else:
        target_code = code_map.get(key, 'zsm_Latn')  # default to Malay not Tamil
    
    return translate_batch(sentences, target_code, fast_mode=fast_mode, num_beams=num_beams)
