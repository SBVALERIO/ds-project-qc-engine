"""One-off diagnostic: dump page size + title-block-strip candidates so we
can tune qc_engine/titleblock.py against a real DS Project Package.

Usage: python -m scripts.inspect_pdf "path/to/package.pdf" [start] [end]
"""

from __future__ import annotations

import sys

import fitz

from qc_engine.titleblock import TITLEBLOCK_X_FRACTION


def main() -> None:
    path = sys.argv[1]
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    end = int(sys.argv[3]) if len(sys.argv) > 3 else start + 3

    with fitz.open(path) as pdf:
        print(f"pages: {pdf.page_count}")
        for index in range(start, min(end, pdf.page_count)):
            page = pdf[index]
            print(f"\n--- page {index + 1} --- size {page.rect.width:.0f} x {page.rect.height:.0f} pt")
            strip_x0 = page.rect.width * TITLEBLOCK_X_FRACTION
            raw = page.get_text("dict")
            spans = []
            for block in raw.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            spans.append(span)

            strip_spans = [s for s in spans if s["bbox"][0] >= strip_x0]
            print(f"  total spans: {len(spans)}, in right-strip (x>={strip_x0:.0f}): {len(strip_spans)}")
            for s in sorted(strip_spans, key=lambda s: -s["size"])[:15]:
                x0, y0, x1, y1 = s["bbox"]
                print(f"    size={s['size']:.1f} pos=({x0:.0f},{y0:.0f}) text={s['text']!r}")


if __name__ == "__main__":
    main()
