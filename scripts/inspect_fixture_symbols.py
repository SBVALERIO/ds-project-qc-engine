"""Looks for small, simple, repeated vector shapes (candidate recessed-
light symbols) on a page, grouped by (item-count, rounded size) so we can
see if any cluster's population roughly matches a legend quantity."""

import sys
from collections import Counter

import fitz

path = sys.argv[1]
page_number = int(sys.argv[2])

with fitz.open(path) as pdf:
    page = pdf[page_number - 1]
    matrix = page.rotation_matrix
    drawings = page.get_drawings()

    print(f"p.{page_number}: {len(drawings)} total drawing paths")

    buckets: Counter[tuple[int, int, int]] = Counter()
    examples: dict[tuple[int, int, int], fitz.Rect] = {}
    for d in drawings:
        rect = d.get("rect")
        if rect is None:
            continue
        rect = fitz.Rect(rect) * matrix
        w, h = rect.width, rect.height
        if w <= 0 or h <= 0 or w > 40 or h > 40:
            continue  # only small, roughly-symbol-sized shapes
        n_items = len(d.get("items", []))
        key = (n_items, round(w), round(h))
        buckets[key] += 1
        examples[key] = rect

    print("small-shape clusters (n_items, width, height) -> count:")
    for key, count in sorted(buckets.items(), key=lambda kv: -kv[1])[:25]:
        rect = examples[key]
        print(f"  n_items={key[0]:3d} size={key[1]}x{key[2]} count={count:4d} example_at=({rect.x0:.0f},{rect.y0:.0f})")
