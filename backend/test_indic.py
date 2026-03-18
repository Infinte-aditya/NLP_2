from transformers import MarianMTModel, MarianTokenizer
import torch

def test_inference():
    model_name = "Helsinki-NLP/opus-mt-en-dra"
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {DEVICE}")

    print("Loading model/tokenizer...")
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name).to(DEVICE)
    model.eval()

    input_text = "Engine oil pressure is low"
    # Prepend language token for Tamil
    input_text_prefixed = ">>tam<< " + input_text
    print(f"Input: {input_text_prefixed}")

    # Tokenize
    batch = tokenizer(
        [input_text_prefixed], 
        return_tensors="pt", 
        padding=True
    ).to(DEVICE)

    # Generate
    with torch.no_grad():
        generated_tokens = model.generate(
            **batch,
            max_length=512,
            num_beams=5,
            num_return_sequences=1,
        )

    # Decode
    translated = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
    print(f"Output: {translated}")

    if len(translated) > 5:
        print("SUCCESS: Model produced output.")
    else:
        print("FAILURE: Model produced empty/short output.")

if __name__ == "__main__":
    test_inference()
