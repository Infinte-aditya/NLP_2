# checklist

##   English automotive technical terms manuals/glossaries


Download them.
Extract the ~1,000–2,000 technical terms.
Add Tamil + Hindi translations (use your improved ai4bharat-transliteration or indic-transliteration + manual review for the first 200–300 critical terms).
Import directly into your english_tamil_hindi_glossary.json.

Top Recommended Glossaries (Automotive-Specific)

1. J1930 (Electrical/Electronic Systems Diagnostic Terms, Definitions, Abbreviations, and Acronyms)
 - https://techinfo.maserati.com/tch/resources/doc/j1930_200204.pdf
2. AA1Car Automotive Glossary



## How to Turn Your NLLB NMT into a “Beast” for Automotive Terms Translation

### Seed a massive domain-specific glossary from SAE J1930 + AA1Car

Pre-load 1,000+ automotive terms with approved Tamil/Hindi translations. Make protect_terms() catch them before NLLB sees the sentence.
Code impact: Extend classify_terms() + one-time import script. Immediate 30–40% accuracy boost on technical nouns.

### Strengthen pre-translation term protection + fuzzy matching

Improve protect_terms() with fuzzy matching (e.g., rapidfuzz) so “voltage regulator”, “synchronizer sleeve”, etc., are caught even if slightly varied.
Code impact: Add rapidfuzz dependency + small change in backend/pipeline/preprocessing.py.

### Better post-translation glossary enforcement (your current weak point)

Upgrade apply_glossary_post_translation() + the updater’s _detect_survivors() to catch more compounds and use the new AI4Bharat transliteration (as we discussed earlier). Lower THRESHOLD to 1 for automotive terms only.
Code impact: Replace transliteration section (already planned) + add domain flag in GlossaryUpdater.

### Hybrid translation: NLLB + glossary-forced replacement

After NLLB, run a second pass that forces glossary terms using exact regex + priority (even if NLLB translated them wrongly). This is “terminology injection” without changing the model.
Code impact: New function in postprocessing.py — very effective for technical docs.

### Collect & fine-tune on automotive parallel data (the real “beast” mode)

Scrape or buy English–Tamil/Hindi automotive service manuals (many Indian OEMs publish bilingual PDFs). Create 50k–100k sentence pairs and fine-tune NLLB with LoRA (low-resource, fits on one GPU).
Code impact: Add translate_batch() to use a fine-tuned model path. Accuracy jumps dramatically for domain.

### Switch to a stronger Indic base model

Replace NLLB-200 with IndicTrans2 or AI4Bharat IndicBART (both far better at Tamil/Hindi technical translation out-of-the-box).
Code impact: Small change in indic_model.py (swap model name + tokenizer).

### Tune generation parameters per domain

For long technical sentences use higher num_beams=4, length_penalty=1.0, and no_repeat_ngram_size=4. Short sentences stay at beam=1.
Code impact: Make num_beams dynamic in make_translation_helper() based on sentence length + keyword presence (e.g., “voltage”, “EGR”).

### Add Translation Memory (TM) lookup before NLLB

Store previously translated sentences/segments in a SQLite DB. If >90% match → reuse exact translation (perfect consistency).
Code impact: New simple TM module — huge win for repetitive manuals.

### Use your /evaluate endpoint for continuous improvement

Run weekly evaluation on new automotive test docs → automatically flag worst segments → add those terms to glossary or fine-tune data.
Code impact: Already built! Just automate it with a cron job + script that extracts poor semantic scores.

### Ensemble / multi-pass approach (nuclear option)

Translate once with NLLB → translate again with a second model (e.g., Google/DeepL API for English → Hindi/Tamil as fallback) → choose the version that matches glossary terms best (via semantic similarity).
Code impact: Add optional second translator in translate_sentences() — expensive but extremely accurate.


first i want to do pdf parsing for the automotive terms
 
but i can see that the document is in image pdf so as not allow text selection
 
so i guess ishoiuld run ocr on this
and then extract the library and then
 
equate all three types as a single meaning word
 
then find the best transliteration for them using ai4bharat as the indictransliteration is not doing the task for me
 
then i will move on to other tasks