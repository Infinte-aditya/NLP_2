"""
Diagnose anchored images in the translated DOCX to find cropping causes.
"""
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

doc = Document("uploads/translated_Sample Input File English.docx")
body = doc.element.body

print("=" * 70)
print("ANCHORED IMAGE DIAGNOSTIC")
print("=" * 70)

anchors = list(body.iter(qn('wp:anchor')))
print(f"\nTotal anchored images found: {len(anchors)}\n")

for i, anchor in enumerate(anchors):
    print(f"--- Anchor #{i+1} ---")
    
    # Size
    extent = anchor.find(qn('wp:extent'))
    if extent is not None:
        cx = int(extent.get('cx', 0))
        cy = int(extent.get('cy', 0))
        print(f"  Size: {cx/914400:.1f}in x {cy/914400:.1f}in ({cx} x {cy} EMU)")
    
    # Vertical position
    pos_v = anchor.find(qn('wp:positionV'))
    if pos_v is not None:
        rel = pos_v.get('relativeFrom', 'unknown')
        off = pos_v.find(qn('wp:posOffset'))
        off_val = off.text if off is not None else 'N/A'
        print(f"  Vertical: relativeFrom='{rel}', offset={off_val}")
    
    # Horizontal position
    pos_h = anchor.find(qn('wp:positionH'))
    if pos_h is not None:
        rel = pos_h.get('relativeFrom', 'unknown')
        off = pos_h.find(qn('wp:posOffset'))
        off_val = off.text if off is not None else 'N/A'
        print(f"  Horizontal: relativeFrom='{rel}', offset={off_val}")
    
    # behindDoc, layoutInCell
    print(f"  behindDoc={anchor.get('behindDoc', '?')}, layoutInCell={anchor.get('layoutInCell', '?')}")
    
    # Check for cropping (a:srcRect)
    src_rects = list(anchor.iter(qn('a:srcRect')))  # drawingML namespace
    if src_rects:
        for sr in src_rects:
            print(f"  *** CROP FOUND: t={sr.get('t','0')} b={sr.get('b','0')} l={sr.get('l','0')} r={sr.get('r','0')}")
    
    # Check if inside a table cell
    parent = anchor.getparent()
    in_table = False
    while parent is not None:
        if parent.tag == qn('w:tc'):
            in_table = True
            break
        parent = parent.getparent()
    print(f"  In table cell: {in_table}")
    
    # Check wrap type
    wrap_types = ['wrapNone', 'wrapSquare', 'wrapTight', 'wrapTopAndBottom', 'wrapThrough']
    for wt in wrap_types:
        if anchor.find(qn(f'wp:{wt}')) is not None:
            print(f"  Wrap type: {wt}")
            break
    
    print()

# Also check inline images
inlines = list(body.iter(qn('wp:inline')))
print(f"Total inline images: {len(inlines)}")

# Check for VML images (v:shape with v:imagedata)
vml_ns = '{urn:schemas-microsoft-com:vml}'
vml_images = list(body.iter(f'{vml_ns}imagedata'))
print(f"Total VML images: {len(vml_images)}")

for i, img in enumerate(vml_images[:5]):
    parent_shape = img.getparent()
    style = parent_shape.get('style', '') if parent_shape is not None else ''
    print(f"  VML Image #{i+1} style: {style[:100]}")
