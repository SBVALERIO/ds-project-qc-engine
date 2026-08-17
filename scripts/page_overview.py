import sys

import fitz

path = sys.argv[1]
page_number = int(sys.argv[2])

with fitz.open(path) as pdf:
    page = pdf[page_number - 1]
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
    print(f"page {page_number}: {page.rect.width:.0f}x{page.rect.height:.0f} rotation={page.rotation}, {len(spans)} spans")
    if spans:
        xs = [r.x0 for r, s in spans]
        ys = [r.y0 for r, s in spans]
        print(f"x range: {min(xs):.0f} - {max(xs):.0f}")
        print(f"y range: {min(ys):.0f} - {max(ys):.0f}")
        print("largest 15 by font size:")
        for rect, s in sorted(spans, key=lambda t: -t[1]["size"])[:15]:
            print(f"  size={s['size']:.1f} x0={rect.x0:.0f} y0={rect.y0:.0f} text={s['text']!r}")
