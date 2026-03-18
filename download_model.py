"""
Download the NLLB-200 model weights to the local Hugging Face cache.
Run this ONCE before starting the backend.
"""
import os
import sys

# Suppress the duplicate-lib warning on Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

print("=" * 60)
print("  NLLB-200 Model Downloader")
print("=" * 60)

MODEL_NAME = "facebook/nllb-200-distilled-600M"

# Step 1: Download tokenizer
print(f"\n[1/3] Downloading tokenizer for {MODEL_NAME}...")
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, force_download=True)
print("      Tokenizer downloaded successfully.")

# Step 2: Download model weights
print(f"\n[2/3] Downloading model weights for {MODEL_NAME}...")
print("      This is ~1.2 GB and may take several minutes.")
print("      Please do NOT close this window.\n")
from transformers import AutoModelForSeq2SeqLM
import torch

model = AutoModelForSeq2SeqLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float32,
    low_cpu_mem_usage=True,
    force_download=True,
)
print("      Model weights downloaded successfully.")

# Step 3: Quick sanity check
print(f"\n[3/3] Running quick sanity check...")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(DEVICE)
model.eval()

tokenizer.src_lang = "eng_Latn"
inputs = tokenizer(["Engine oil pressure is low"], return_tensors="pt", padding=True, truncation=True).to(DEVICE)
with torch.no_grad():
    outputs = model.generate(
        **inputs,
        forced_bos_token_id=tokenizer.convert_tokens_to_ids("tam_Taml"),
        max_length=64,
    )
decoded = tokenizer.batch_decode(outputs, skip_special_tokens=True)
print(f"      Test translation (Tamil): {decoded[0]}")

print("\n" + "=" * 60)
print("  SUCCESS! Model is ready. You can now start the backend.")
print("=" * 60)
