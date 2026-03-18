import sys
import os
import torch

# Ensure backend can be imported
sys.path.append(os.getcwd())

from backend.pipeline.indic_model import load_indic_model, translate_batch
from backend.pipeline.preprocessing import load_glossary, classify_terms, protect_terms
from backend.pipeline.postprocessing import restore_placeholders
from backend.pipeline.translation import translate_sentences

def test_full_pipeline():
    print("Testing Full Pipeline Hang...")
    try:
        os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
        
        target_lang = "Tamil"
        sentences = ["Hello world, this is a test.", "Air Bag is a safety device.", "The internal combustion engine is complex."]
        
        print("1. Loading Glossary...")
        full_glossary = load_glossary("english_tamil_hindi_glossary.json")
        protected_glossary, _ = classify_terms(full_glossary, target_lang)
        print(f"Glossary loaded. Protected terms: {len(protected_glossary)}")

        print("2. Protecting Terms...")
        protected_sentences = []
        maps = []
        for s in sentences:
            p_s, m = protect_terms(s, protected_glossary)
            protected_sentences.append(p_s)
            maps.append(m)
        print(f"Protected: {protected_sentences}")

        print("3. Translating (This is where it likely hangs)...")
        # Load model first to see timing
        load_indic_model()
        
        print("Model loaded. Starting generation...")
        translated_batch = translate_sentences(protected_sentences, target_lang=target_lang)
        print(f"Translated: {translated_batch}")

        print("4. Restoring...")
        final_sentences = []
        for i, trans_s in enumerate(translated_batch):
            restored = restore_placeholders(trans_s, maps[i])
            final_sentences.append(restored)
        print(f"Final Success: {final_sentences}")

    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_full_pipeline()
