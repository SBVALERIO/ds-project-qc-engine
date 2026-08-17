import sys

import fitz

path = sys.argv[1]
page_index = int(sys.argv[2]) if len(sys.argv) > 2 else 0

with fitz.open(path) as pdf:
    page = pdf[page_index]
    raw = page.get_text("dict")
    matrix = page.rotation_matrix
    spans = []
    for block in raw.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                t = span.get("text", "").strip()
                if t:
                    rect = fitz.Rect(span["bbox"]) * matrix
                    spans.append((rect, span))
    spans.sort(key=lambda item: -item[0].x0)
    print("page width", page.rect.width, "height", page.rect.height)
    print("rightmost 25 spans by x0 (rotation-corrected):")
    for rect, s in spans[:25]:
        print(f"  x0={rect.x0:.0f} y0={rect.y0:.0f} size={s['size']:.1f} text={s['text']!r}")
