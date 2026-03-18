"""
Find the anchor that's causing the blank page (1E-14).
Look at page-relative anchors, their sizes, and what paragraph they're attached to.
"""
from docx import Document
from docx.oxml.ns import qn
from lxml import etree
import re

doc = Document("uploads/translated_Sample Input File English.docx")
body = doc.element.body

print("=" * 70)
print("BLANK PAGE ANALYSIS")
print("=" * 70)

# Look for the very large page-relative anchors that span entire pages
print("\n--- LARGE PAGE-RELATIVE ANCHORS (potential blank page causes) ---")
for i, anchor in enumerate(body.iter(qn('wp:anchor'))):
    extent = anchor.find(qn('wp:extent'))
    pos_v = anchor.find(qn('wp:positionV'))
    pos_h = anchor.find(qn('wp:positionH'))
    
    cx = int(extent.get('cx', '0')) if extent is not None else 0
    cy = int(extent.get('cy', '0')) if extent is not None else 0
    
    if pos_v is not None:
        rel_v = pos_v.get('relativeFrom', '')
        off_v = pos_v.find(qn('wp:posOffset'))
        off_v_val = int(off_v.text) if off_v is not None and off_v.text else 0
    else:
        rel_v, off_v_val = 'unknown', 0
    
    if pos_h is not None:
        rel_h = pos_h.get('relativeFrom', '')
        off_h = pos_h.find(qn('wp:posOffset'))
        off_h_val = int(off_h.text) if off_h is not None and off_h.text else 0
    else:
        rel_h, off_h_val = 'unknown', 0
    
    # Focus on very tall page-relative images
    cy_in = cy / 914400
    if cy_in > 5 and rel_v == 'page':
        print(f"\nAnchor #{i+1}: {cx/914400:.2f}in x {cy_in:.2f}in")
        print(f"  V: relFrom={rel_v}, offset={off_v_val} ({off_v_val/914400:.2f}in)")
        print(f"  H: relFrom={rel_h}, offset={off_h_val}")
        print(f"  behindDoc={anchor.get('behindDoc','?')}")
        
        # Find parent paragraph text
        p = anchor.getparent()
        while p is not None and p.tag != qn('w:p'):
            p = p.getparent()
        if p is not None:
            text = ''.join(t.text or '' for t in p.iter(qn('w:t')))
            print(f"  Anchor para text: '{text[:80]}'")

# Also look for sectPr to understand page boundaries
print("\n--- INTERMEDIATE SECTION BOUNDARIES ---")
all_sects = list(body.iter(qn('w:sectPr')))
print(f"Total section properties: {len(all_sects)}")
for i, sect in enumerate(all_sects[:-1]):
    t = sect.find(qn('w:type'))
    t_val = t.get(qn('w:val'), 'unset') if t is not None else 'unset'
    # Find preceding paragraph text
    parent = sect.getparent()
    text = ''
    if parent is not None:
        text = ''.join(t2.text or '' for t2 in parent.iter(qn('w:t')))
    print(f"  Sect #{i+1}: type={t_val}, para='{text[:60]}'")

# Check anchors with huge cy that might be transparent vertical bars
print("\n--- VERY TALL NARROW ANCHORS (vertical bar images) ---")
for i, anchor in enumerate(body.iter(qn('wp:anchor'))):
    extent = anchor.find(qn('wp:extent'))
    cx = int(extent.get('cx', '0')) if extent is not None else 0
    cy = int(extent.get('cy', '0')) if extent is not None else 0
    
    cy_in = cy / 914400
    cx_in = cx / 914400
    
    if cy_in > 8 and cx_in < 0.2:
        pos_v = anchor.find(qn('wp:positionV'))
        rel_v = pos_v.get('relativeFrom', '') if pos_v is not None else '?'
        off_v = pos_v.find(qn('wp:posOffset')) if pos_v is not None else None
        off_v_val = off_v.text if off_v is not None else '?'
        print(f"  Anchor #{i+1}: {cx_in:.3f}in x {cy_in:.2f}in, V={rel_v}/offset={off_v_val}")
        
        wrap_tb = anchor.find(qn('wp:wrapTopAndBottom'))
        if wrap_tb is not None:
            print(f"    HAS wrapTopAndBottom! distT={wrap_tb.get('distT','?')}")
