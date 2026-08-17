"""Dumps every rotation-corrected span in the right-edge strip, sorted top
to bottom, so we can read the whole title block layout at once."""

import sys

import fitz

path = sys.argv[1]
page_index = int(sys.argv[2]) if len(sys.argv) > 2 else 0
x_fraction = float(sys.argv[3]) if len(sys.argv) > 3 else 0.85

with fitz.open(path) as pdf:
    page = pdf[page_index]
    raw = page.get_text("dict")
    matrix = page.rotation_matrix
    strip_x0 = page.rect.width * x_fraction
    spans = []
    for block in raw.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                t = span.get("text", "").strip()
                if not t:
                    continue
                rect = fitz.Rect(span["bbox"]) * matrix
                if rect.x0 >= strip_x0:
                    spans.append((rect, span))
    spans.sort(key=lambda item: item[0].y0)
    print(f"page {page_index + 1}: {page.rect.width:.0f}x{page.rect.height:.0f}, strip x>={strip_x0:.0f}")
    for rect, s in spans:
        print(f"  y0={rect.y0:6.0f} x0={rect.x0:6.0f} size={s['size']:5.1f} text={s['text']!r}")
