"""
HTML-based translation pipeline for DOCX documents.

Flow: DOCX → HTML (LibreOffice) → extract text → translate → apply → PDF (LibreOffice)
"""

import os
import subprocess
import shutil
from bs4 import BeautifulSoup, NavigableString

# LibreOffice path on Windows
SOFFICE_PATH = r"C:\Program Files\LibreOffice\program\soffice.exe"

# Tags to skip when extracting text
SKIP_TAGS = {"script", "style", "meta", "link", "title"}

# Tags whose text content should be translated
TEXT_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th", "span", "font", "b", "i", "u", "em", "strong"}


def docx_to_html(input_path: str, output_dir: str) -> str:
    """
    Convert a DOCX file to HTML using LibreOffice headless.
    
    Returns the path to the generated HTML file.
    Images are extracted as separate files in the same directory.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    cmd = [
        SOFFICE_PATH,
        "--headless",
        "--convert-to", "html",
        "--outdir", output_dir,
        input_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")
    
    # Find the generated HTML file
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    html_path = os.path.join(output_dir, f"{base_name}.html")
    
    if not os.path.exists(html_path):
        # Sometimes extension might differ
        for f in os.listdir(output_dir):
            if f.endswith(".html") or f.endswith(".htm"):
                html_path = os.path.join(output_dir, f)
                break
    
    if not os.path.exists(html_path):
        raise FileNotFoundError(f"HTML output not found in {output_dir}")
    
    return html_path


def extract_text_nodes(soup: BeautifulSoup) -> list:
    """
    Extract translatable text nodes from parsed HTML.
    
    Returns a list of (NavigableString, original_text) tuples.
    Only extracts leaf text nodes that contain actual content (not just whitespace).
    Skips image alt text, script/style content, and purely numeric/code references.
    """
    text_nodes = []
    
    for text_node in soup.find_all(string=True):
        # Skip nodes in non-translatable tags
        parent = text_node.parent
        if parent and parent.name in SKIP_TAGS:
            continue
        
        # Skip the sdfield elements (page numbers, etc.)
        if parent and parent.name == "sdfield":
            continue
        
        # Get the text content
        text = str(text_node).strip()
        
        # Skip empty or whitespace-only
        if not text:
            continue
        
        # Skip very short content that's likely formatting artifacts
        # (single characters, just numbers, just punctuation)
        if len(text) <= 1 and not text.isalpha():
            continue
        
        # Skip pure HTML entities or spacing spans
        if text in ('\xa0', '\n', '\r', '\r\n', '\t'):
            continue
            
        text_nodes.append((text_node, text))
    
    return text_nodes


def _is_translatable(text: str) -> bool:
    """Check if text contains actual translatable content (has letters)."""
    return any(c.isalpha() for c in text)


def get_translatable_segments(text_nodes: list) -> tuple:
    """
    From extracted text nodes, identify which ones need translation.
    
    Returns:
        - translatable_indices: list of indices into text_nodes that need translation
        - texts_to_translate: the corresponding text strings
    """
    translatable_indices = []
    texts_to_translate = []
    
    for i, (node, text) in enumerate(text_nodes):
        if _is_translatable(text):
            translatable_indices.append(i)
            texts_to_translate.append(text)
    
    return translatable_indices, texts_to_translate


def apply_translations(text_nodes: list, translatable_indices: list, translated_texts: list):
    """
    Replace text nodes with their translations.
    
    Modifies the soup in-place by replacing NavigableString content.
    Only replaces nodes at the specified indices.
    """
    for idx, translated in zip(translatable_indices, translated_texts):
        node, original = text_nodes[idx]
        
        if translated and translated.strip():
            # Replace the text node content, preserving surrounding whitespace
            original_str = str(node)
            leading_ws = ""
            trailing_ws = ""
            
            # Preserve leading whitespace from original
            for ch in original_str:
                if ch in (' ', '\t', '\n', '\r'):
                    leading_ws += ch
                else:
                    break
            
            # Preserve trailing whitespace from original
            for ch in reversed(original_str):
                if ch in (' ', '\t', '\n', '\r'):
                    trailing_ws = ch + trailing_ws
                else:
                    break
            
            new_text = leading_ws + translated.strip() + trailing_ws
            node.replace_with(NavigableString(new_text))


def inject_indic_font_css(soup: BeautifulSoup):
    """
    Add CSS to the HTML to ensure Indic fonts render correctly.
    Adds NirmalaUI font-face and sets it as a fallback on body.
    """
    windir = os.environ.get("WINDIR", r"C:\Windows")
    nirmala_path = os.path.join(windir, "Fonts", "Nirmala.ttf").replace("\\", "/")
    
    style_tag = soup.new_tag("style")
    style_tag.string = f"""
    @font-face {{
        font-family: 'NirmalaUI';
        src: url('file:///{nirmala_path}');
    }}
    body, p, h1, h2, h3, h4, h5, h6, li, td, th, span, font, b, i, u, em, strong {{
        font-family: 'NirmalaUI', 'Nirmala UI', 'Arial', sans-serif !important;
    }}
    """
    
    head = soup.find("head")
    if head:
        head.append(style_tag)
    else:
        soup.insert(0, style_tag)


def html_to_pdf(html_path: str, pdf_path: str) -> str:
    """
    Convert HTML to PDF using LibreOffice headless.
    
    Returns the path to the generated PDF file.
    """
    output_dir = os.path.dirname(pdf_path)
    os.makedirs(output_dir, exist_ok=True)
    
    cmd = [
        SOFFICE_PATH,
        "--headless",
        "--convert-to", "pdf",
        "--outdir", output_dir,
        html_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    if result.returncode != 0:
        raise RuntimeError(f"HTML to PDF conversion failed: {result.stderr}")
    
    # LibreOffice names the PDF based on the input HTML filename
    base_name = os.path.splitext(os.path.basename(html_path))[0]
    generated_pdf = os.path.join(output_dir, f"{base_name}.pdf")
    
    # Rename to desired output path if different
    if os.path.exists(generated_pdf) and generated_pdf != pdf_path:
        shutil.move(generated_pdf, pdf_path)
    elif not os.path.exists(generated_pdf) and not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF output not found at {generated_pdf}")
    
    return pdf_path


def translate_html_pipeline(
    input_docx: str,
    output_pdf: str,
    translation_helper,
    target_lang: str,
    progress_callback=None
) -> str:
    """
    Full pipeline: DOCX → HTML → extract text → translate → apply → PDF.
    
    Args:
        input_docx: Path to the input DOCX file
        output_pdf: Path for the output PDF file
        translation_helper: Function that takes (sentences, lang_code) and returns translated sentences
        target_lang: Target language (e.g., "Tamil", "Hindi")
        progress_callback: Optional callback(stage_text, percent)
    
    Returns:
        Path to the generated PDF
    """
    work_dir = os.path.join(os.path.dirname(output_pdf), "_html_work")
    
    try:
        # Step 1: DOCX → HTML
        if progress_callback:
            progress_callback("Converting document to HTML...", 30)
        
        html_path = docx_to_html(input_docx, work_dir)
        print(f"[HTML Pipeline] DOCX → HTML: {html_path}")
        
        # Step 2: Parse HTML and extract text nodes
        if progress_callback:
            progress_callback("Extracting text from document...", 35)
        
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, "html.parser")
        text_nodes = extract_text_nodes(soup)
        translatable_indices, texts_to_translate = get_translatable_segments(text_nodes)
        
        print(f"[HTML Pipeline] Found {len(text_nodes)} text nodes, {len(texts_to_translate)} translatable")
        
        if not texts_to_translate:
            print("[HTML Pipeline] No translatable text found!")
            # Still produce a PDF from the original
            inject_indic_font_css(soup)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(str(soup))
            return html_to_pdf(html_path, output_pdf)
        
        # Step 3: Translate
        if progress_callback:
            progress_callback("Translating text segments...", 40)
        
        translated_texts = translation_helper(
            texts_to_translate, target_lang, 
            progress_callback=progress_callback
        )
        
        print(f"[HTML Pipeline] Translated {len(translated_texts)} segments")
        
        # Step 4: Apply translations back into HTML
        if progress_callback:
            progress_callback("Applying translations to document...", 90)
        
        apply_translations(text_nodes, translatable_indices, translated_texts)
        
        # Step 5: Inject Indic font CSS
        inject_indic_font_css(soup)
        
        # Save translated HTML
        translated_html_path = os.path.join(work_dir, "translated.html")
        with open(translated_html_path, "w", encoding="utf-8") as f:
            f.write(str(soup))
        
        print(f"[HTML Pipeline] Saved translated HTML: {translated_html_path}")
        
        # Step 6: HTML → PDF
        if progress_callback:
            progress_callback("Converting to PDF...", 95)
        
        result_pdf = html_to_pdf(translated_html_path, output_pdf)
        print(f"[HTML Pipeline] Generated PDF: {result_pdf}")
        
        return result_pdf
        
    except Exception as e:
        print(f"[HTML Pipeline] Error: {e}")
        import traceback
        traceback.print_exc()
        raise
