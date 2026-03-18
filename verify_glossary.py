import sys
import os
import json

sys.path.append(os.getcwd())
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass # Python < 3.7 or not a TTY

from backend.pipeline.preprocessing import load_glossary, classify_terms, protect_terms
from backend.pipeline.postprocessing import restore_placeholders

def test_glossary():
    print("Testing Glossary Enforcement...")
    
    # Create dummy glossary
    dummy_glossary = {
        "Air Bag": {"ta": "ஏர் பேக்", "hi": "एअर बॅग"},
        "Engine": {"ta": "என்ஜின்", "hi": "इंजिन"}
    }
    
    with open("dummy_glossary.json", "w", encoding="utf-8") as f:
        json.dump(dummy_glossary, f)
        
    # Load
    glossary = load_glossary("dummy_glossary.json")
    protected_ta, _ = classify_terms(glossary, "Tamil")
    
    # Test Sentence
    sent = "The Air Bag deployed near the Engine."
    print(f"Original: {sent}")
    
    # Protect
    p_sent, term_map = protect_terms(sent, protected_ta)
    print(f"Protected: {p_sent}")
    print(f"Map: {term_map}")
    
    # Simulate Translation (The placeholder should survive)
    # e.g. "__TERM_0__ deployed near the __TERM_1__." -> "__TERM_0__ அருகில் __TERM_1__ வரிசைப்படுத்தப்பட்டது."
    translated_simulated = p_sent.replace("The", "").replace("deployed near the", "அருகில்").replace(".", "") + " செயல்பட்டது"
    print(f"Simulated Trans: {translated_simulated}")
    
    # Restore
    final = restore_placeholders(translated_simulated, term_map)
    print(f"Final: {final}")
    
    # Check
    if "ஏர் பேக்" in final and "என்ஜின்" in final:
        print("SUCCESS: Glossary terms found in final output.")
    else:
        print("FAILURE: Glossary terms missing.")

if __name__ == "__main__":
    test_glossary()
