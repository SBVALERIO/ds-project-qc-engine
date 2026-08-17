"""Dumps every span outside the title-block strip for a page, sorted
reading order (top-to-bottom, then left-to-right), to study legend/
schedule layout."""

import sys

from qc_engine.pdf_ingest import load_document
from qc_engine.titleblock import TITLEBLOCK_X_FRACTION

path = sys.argv[1]
page_number = int(sys.argv[2])

document = load_document(path)
page = document.pages[page_number - 1]
print(f"p.{page.number} {page.sheet_number} — {page.sheet_title}")
strip_x0 = page.width * TITLEBLOCK_X_FRACTION
body_spans = [s for s in page.spans if s.x0 < strip_x0]
body_spans.sort(key=lambda s: (round(s.y0 / 5), s.x0))
for s in body_spans:
    print(f"  x0={s.x0:6.0f} y0={s.y0:6.0f} size={s.size:5.1f} {s.text!r}")
