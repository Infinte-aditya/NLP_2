import re

class IndicProcessor:
    def __init__(self, inference=True):
        self.inference = inference

    def preprocess_batch(self, batch, src_lang, tgt_lang):
        """
        Preprocess batch for IndicTrans2.
        Adds language tags and handles transliteration if needed.
        """
        processed_batch = []
        for sentence in batch:
            # IndicTrans2 format: [src_lang] sentence [tgt_lang]
            # Actually, looking at the user snippet:
            # batch = ip.preprocess_batch(input_sentences, src_lang=src_lang, tgt_lang=tgt_lang)
            # tokenizer(batch, ...)
            
            # The library typically formats as:
            # "src_lang: sentence tgt_lang" or similar?
            # No, user said: "src_lang: input_sentence" in output print.
            
            # Based on standard IndicTrans2 usage (from their README/Paper):
            # Input: "sentence"
            # Src Lang Token: "__src__" ? No, they use FLORES codes.
            
            # The official processor does this (roughly):
            # return [f"{sentence} </s> {tgt_lang}" for sentence in batch] ??
            # Wait, src_lang is also needed.
            
            # User snippet: 
            # inputs = tokenizer(batch, ...)
            # model.generate(**inputs, ...)
            
            # If I look at the tokenizer_indictrans.py I saw earlier:
            # _src_tokenize: src_lang, tgt_lang, text = text.split(" ", 2)
            # return [src_lang, tgt_lang] + self.spm.EncodeAsPieces(text)
            
            # So the input string MUST be: "src_lang tgt_lang sentence"
            # Example: "eng_Latn hin_Deva Hello world"
            
            processed_sentence = f"{src_lang} {tgt_lang} {sentence}"
            processed_batch.append(processed_sentence)
            
        return processed_batch

    def postprocess_batch(self, batch, lang):
        """
        Postprocess batch.
        """
        # IndicTrans2 might output some artifacts or need script conversion.
        # For now, we just return as is, or strip special tokens if any remain (tokenizer.batch_decode usually handles special tokens).
        # The user snippet does: tokenizer.batch_decode(..., skip_special_tokens=True) -> then postprocess_batch.
        
        # We'll assume simple strip for now.
        return [s.strip() for s in batch]
