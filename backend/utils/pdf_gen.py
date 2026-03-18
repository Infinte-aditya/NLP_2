from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import urllib.request
import zipfile
import glob
import re

def generate_pdf(translated_text: str, output_path: str):
    """
    Generates a PDF file from translated text.
    Handles Tamil and Hindi font registration on Windows.
    """
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    
    # Font configuration for Windows
    font_name = "Helvetica"  # Final fallback
    
    # Build font candidate list
    windir = os.environ.get("WINDIR", "C:\\Windows")
    localappdata = os.environ.get("LOCALAPPDATA", "")
    
    font_candidates = [
        # Standard Windows system fonts
        ("NirmalaUI", os.path.join(windir, "Fonts", "Nirmala.ttf")),
        ("Latha", os.path.join(windir, "Fonts", "latha.ttf")),
        ("Mangal", os.path.join(windir, "Fonts", "mangal.ttf")),
        ("ArialUnicode", os.path.join(windir, "Fonts", "ARIALUNI.TTF")),
        # User-installed fonts (Windows)
        ("NirmalaUI", os.path.join(localappdata, "Microsoft", "Windows", "Fonts", "Nirmala.ttf")),
        ("Latha", os.path.join(localappdata, "Microsoft", "Windows", "Fonts", "latha.ttf")),
        ("Mangal", os.path.join(localappdata, "Microsoft", "Windows", "Fonts", "mangal.ttf")),
        # macOS fonts
        ("Tamil", "/System/Library/Fonts/Supplemental/Tamil MN.ttc"),
        ("Hindi", "/System/Library/Fonts/Supplemental/DevanagariMT.ttc"),
    ]
    
    # Also check for any Noto Sans fonts in the project directory
    noto_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "fonts")
    if os.path.isdir(noto_dir):
        for ttf in glob.glob(os.path.join(noto_dir, "*.ttf")):
            name = os.path.splitext(os.path.basename(ttf))[0].replace("-", "")
            font_candidates.append((name, ttf))
    
    registered_fonts = {}
    
    for name, path in font_candidates:
        if name in registered_fonts:
            continue  # Already registered
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                registered_fonts[name] = path
                print(f"Registered font: {name} from {path}")
            except Exception as e:
                print(f"Could not register font {name}: {e}")
    
    # Pick the best font based on what's available
    # Prefer NirmalaUI as it covers both Tamil and Hindi
    if "NirmalaUI" in registered_fonts:
        font_name = "NirmalaUI"
    elif "ArialUnicode" in registered_fonts:
        font_name = "ArialUnicode"
    else:
        # Check text content and pick specific font
        has_devanagari = any('\u0900' <= char <= '\u097F' for char in translated_text)
        has_tamil = any('\u0B80' <= char <= '\u0BFF' for char in translated_text)
        
        if has_tamil and "Latha" in registered_fonts:
            font_name = "Latha"
        elif has_tamil and "Tamil" in registered_fonts:
            font_name = "Tamil"
        elif has_devanagari and "Mangal" in registered_fonts:
            font_name = "Mangal"
        elif has_devanagari and "Hindi" in registered_fonts:
            font_name = "Hindi"
    
    print(f"Using font: {font_name}")
    
    try:
        c.setFont(font_name, 12)
    except Exception as e:
        print(f"Font error, falling back to Helvetica: {e}")
        c.setFont("Helvetica", 12)
        
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import yellow
    from reportlab.lib.utils import escape
    
    # Create the PDF document with tighter margins to preserve layout
    doc = SimpleDocTemplate(
        output_path, 
        pagesize=letter,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    story = []
    styles = getSampleStyleSheet()
    
    # Create a custom style with the Indic font and tighter layout
    custom_style = ParagraphStyle(
        'CustomIndic',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=11,
        leading=14,
        spaceAfter=6,
    )
    
    # Process text for markers: @@term@@ -> <font backColor="yellow">term</font>
    content = translated_text
    
    # Helper to convert markers to ReportLab markup
    def markup_text(text):
        # 1. Escape basic XML
        text = escape(text)
        # 2. Convert markers
        text = re.sub(r'@@(.*?)@@', r'<font backcolor="yellow">\1</font>', text)
        return text

    # Split into entries/paragraphs
    paragraphs = content.split('\n')
    for p_text in paragraphs:
        p_text = p_text.strip()
        if not p_text:
            story.append(Spacer(1, 8))
            continue
            
        markup = markup_text(p_text)
        story.append(Paragraph(markup, custom_style))
        
    doc.build(story)
    return output_path
