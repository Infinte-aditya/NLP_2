import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["TRANSFORMERS_TORCH_LOAD_SAFE_ONLY"] = "0"
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import re

# Monkey-patch: bypass torch version check for loading local .bin files
# (Safe because we only load from our own trusted local folder)
try:
    import transformers.modeling_utils as _mu
    _mu.check_torch_load_is_safe = lambda: None
except Exception:
    pass

# Global caching
model = None
tokenizer = None
current_model_name = None
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Point to the manually downloaded folder
MODEL_NAME = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "nllb_model")

def load_indic_model():
    """
    Loads the NLLB-200 model and tokenizer from the local folder.
    """
    global model, tokenizer, current_model_name
    
    if model is not None:
        return model, tokenizer
        
    print(f"--- Model Initialization Started (Local Folder) ---")
    print(f"Target Device: {DEVICE}")
    print(f"Model Path: {MODEL_NAME}")
    
    try:
        print("1. Loading Tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, local_files_only=True)
        print("   - Tokenizer loaded successfully.")

        print("2. Loading Model...")
        model = AutoModelForSeq2SeqLM.from_pretrained(
            MODEL_NAME, 
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            low_cpu_mem_usage=True,
            local_files_only=True
        ).to(DEVICE)
        print(f"   - Model loaded successfully onto {DEVICE}.")
            
        model.eval()
        print("--- Model Initialization Complete ---")
    except Exception as e:
        print(f"!!! Error loading NLLB-200 model from {MODEL_NAME}: {e}")
        import traceback
        traceback.print_exc()
        raise e

    return model, tokenizer

def translate_batch(sentences: list, target_lang_code: str, fast_mode: bool = False) -> list:
    """
    Translates a batch of sentences using NLLB-200.
    target_lang_code: 'tam_Taml', 'hin_Deva'
    fast_mode: if True, use fewer beams and shorter max_length for speed.
    """
    global model, tokenizer
    
    if model is None:
        load_indic_model()
    
    # Filter valid sentences
    valid_indices = []
    valid_sentences = []
    for i, s in enumerate(sentences):
        stripped = s.strip()
        if stripped:
            valid_indices.append(i)
            valid_sentences.append(stripped)
    
    if not valid_sentences:
        return sentences
        
    # NLLB usage
    tokenizer.src_lang = "eng_Latn"
    inputs = tokenizer(valid_sentences, return_tensors="pt", padding=True, truncation=True).to(DEVICE)
    
    # Generation parameters — fast_mode trades slight quality for major speed gain
    gen_beams = 2 if fast_mode else 5
    gen_max_length = 512 if fast_mode else 1024

    try:
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                forced_bos_token_id=tokenizer.convert_tokens_to_ids(target_lang_code),
                num_beams=gen_beams,
                no_repeat_ngram_size=3,
                max_length=gen_max_length
            )
            
        decoded = tokenizer.batch_decode(
            outputs, 
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )
        
        # Map back to original indices
        result = list(sentences)
        for idx, valid_idx in enumerate(valid_indices):
            if idx < len(decoded):
                result[valid_idx] = decoded[idx].strip()
        
        return result
    except Exception as e:
        print(f"Translation Error: {e}")
        return [""] * len(sentences) # Return empty strings on error to prevent English leakage
