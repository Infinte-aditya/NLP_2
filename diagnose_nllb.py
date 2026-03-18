import os
os.environ["HF_HUB_OFFLINE"] = "1"
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import time

MODEL_NAME = "facebook/nllb-200-distilled-600M"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"--- Diagnostic Start ---")
print(f"Device: {DEVICE}")

try:
    print("1. Loading tokenizer (local-first)...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, local_files_only=True)
        print("   Tokenizer loaded from local cache.")
    except Exception:
        print("   Local tokenizer not found. Attempting online fetch...")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        print("   Tokenizer fetched.")

    print(f"2. Loading model {MODEL_NAME} to {DEVICE} (local-first)...")
    start = time.time()
    try:
        model = AutoModelForSeq2SeqLM.from_pretrained(
            MODEL_NAME, 
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            low_cpu_mem_usage=True,
            local_files_only=True
        ).to(DEVICE)
        print(f"   Model loaded from local cache in {time.time() - start:.2f} seconds.")
    except Exception:
        print("   Local model not found. Attempting online fetch...")
        model = AutoModelForSeq2SeqLM.from_pretrained(
            MODEL_NAME, 
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            low_cpu_mem_usage=True
        ).to(DEVICE)
        print(f"   Model fetched and loaded in {time.time() - start:.2f} seconds.")

    print("3. Running test translation...")
    sentences = ["The engine is working well."]
    tokenizer.src_lang = "eng_Latn"
    inputs = tokenizer(sentences, return_tensors="pt", padding=True, truncation=True).to(DEVICE)
    
    print("   Generating output...")
    start = time.time()
    outputs = model.generate(
        **inputs,
        forced_bos_token_id=tokenizer.convert_tokens_to_ids("tam_Taml"),
        max_length=64
    )
    decoded = tokenizer.batch_decode(outputs, skip_special_tokens=True)
    print(f"   Translation (Tamil): {decoded[0]}")
    print(f"   Inference took {time.time() - start:.2f} seconds.")
    print("--- SUCCESS ---")
except Exception as e:
    print(f"--- FAILURE ---")
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
