import torch
from backend.pipeline.indic_model import translate_batch

def test_inference():
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {DEVICE}")

    sentences = ["Engine oil pressure is low", "Check brake fluid level"]
    target_code = "tam_Taml" # Tamil
    
    print(f"Testing NLLB-200 Translation to {target_code}...")
    
    try:
        results = translate_batch(sentences, target_code)
        for i, res in enumerate(results):
            print(f"Input {i+1}: {sentences[i]}")
            print(f"Output {i+1}: {res}\n")
            
        if any(len(res) > 5 for res in results):
            print("SUCCESS: NLLB-200 produced output.")
        else:
            print("FAILURE: NLLB-200 produced empty/short output.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_inference()
