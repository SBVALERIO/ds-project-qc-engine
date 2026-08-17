import sys

import fitz

path = sys.argv[1]
page_number = int(sys.argv[2])

with fitz.open(path) as pdf:
    page = pdf[page_number - 1]
    matrix = page.rotation_matrix
    drawings = page.get_drawings()

    red = []
    for d in drawings:
        color = d.get("color")
        if not color or color[0] < 0.6 or color[1] > 0.35 or color[2] > 0.35:
            continue
        rect = d.get("rect")
        if rect is None:
            continue
        rect = fitz.Rect(rect) * matrix
        n_items = len(d.get("items", []))
        red.append((n_items, rect, d.get("type")))

    red.sort(key=lambda t: -t[0])
    print(f"{len(red)} red-ish paths on p.{page_number}")
    for n_items, rect, dtype in red[:40]:
        w, h = rect.width, rect.height
        print(f"  n_items={n_items:4d} type={dtype} rect=({rect.x0:.0f},{rect.y0:.0f})-({rect.x1:.0f},{rect.y1:.0f}) size={w:.0f}x{h:.0f}")
