import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from backend.pipeline.preprocessing import protect_terms, load_glossary, classify_terms
from backend.pipeline.postprocessing import restore_placeholders

# Mock glossary
glossary_data = {
    "Air Bag": {"ta": "ஏர் பேக்", "hi": "एअर बैग"},
    "Engine": {"ta": "என்ஜின்", "hi": "इंजन"}
}

def test_glossary_protection():
    print("Testing Glossary Protection...")
    
    # Setup
    input_text = "The Air Bag is deployed accurately."
    target_lang = "ta"
    
    # simplified classify
    protected_glossary = {"Air Bag": "ஏர் பேக்"} 
    
    # 1. Protect
    print(f"Input: {input_text}")
    protected_text, ph_map = protect_terms(input_text, protected_glossary)
    print(f"Protected: {protected_text}")
    print(f"Map: {ph_map}")
    
    assert "__TERM_" in protected_text
    assert "Air Bag" not in protected_text
    
    # 2. Simulate Translation (Mocking model behavior)
    # Assume model keeps placeholder but translates surrounding text
    # "The __TERM_0__ is deployed accurately." -> "துல்லியமாக __TERM_0__ பயன்படுத்தப்பட்டது."
    translated_text_mock = f"துல்லியமாக {protected_text.replace('The ', '').replace(' is deployed accurately.', '')} பயன்படுத்தப்பட்டது." 
    # Wait, protected_text is "__TERM_0__ is deployed..." 
    # Let's just construct a mock string
    
    placeholder = list(ph_map.keys())[0]
    translated_mock = f"துல்லியமாக {placeholder} பயன்படுத்தப்பட்டது."
    print(f"Translated (Mock): {translated_mock}")
    
    # 3. Restore
    final_text = restore_placeholders(translated_mock, ph_map)
    print(f"Restored: {final_text}")
    
    assert "ஏர் பேக்" in final_text
    assert "__TERM_" not in final_text
    
    print("SUCCESS: Glossary protection flow works.\n")

def test_mangled_placeholders():
    print("Testing Last Resort & Garbage Cleanup...")
    
    # Setup
    ph_map = {"__TERM_0__": "எஞ்சின்", "__TERM_1__": "டயர்கள்"}
    
    # Realistic garbage cases seen in screenshots
    mangled_cases = [
        "Heading Title _ _",             # Trailing underscores
        "Sentence with __ 01 __ here.",   # Letterless placeholder
        "Broken __ __ artifact.",         # Empty placeholder bits
        "Multiple    spaces    test.",    # Space normalization
    ]
    
    for case in mangled_cases:
        restored = restore_placeholders(case, ph_map, highlight=True)
        print(f"Input: {case}")
        print(f"Restored: {restored}")
        
        if "Heading" in case:
            assert "_" not in restored
        if "01" in case:
            assert "@@" in restored
        if "artifact" in case:
            assert "__" not in restored
            
        assert "  " not in restored
        print("Success for this case.")
    
    print("SUCCESS: Final polish logic works.\n")

def test_error_handling_mock():
    print("Testing Error Handling (Concept)...")
    sentences = ["Error case"]
    translated_batch = [""] 
    final_sentences = []
    placeholder_maps = [{}]
    
    # Logic from main.py
    for i, trans_s in enumerate(translated_batch):
        if not trans_s:
            final_sentences.append("")
            continue
        restored = restore_placeholders(trans_s, placeholder_maps[i], highlight=True)
        final_sentences.append(restored)
        
    print(f"Result for error input: '{final_sentences[0]}'")
    assert final_sentences[0] == ""
    print("SUCCESS: Error handling produces empty string.\n")

if __name__ == "__main__":
    test_glossary_protection()
    test_mangled_placeholders()
    test_error_handling_mock()
