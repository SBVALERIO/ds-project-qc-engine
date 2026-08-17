import sys

from qc_engine.pdf_ingest import load_document
from qc_engine.titleblock import TITLEBLOCK_X_FRACTION

path = sys.argv[1]
needle = sys.argv[2] if len(sys.argv) > 2 else "CASA@63"

document = load_document(path)
for page in document.pages:
    strip_x0 = page.width * TITLEBLOCK_X_FRACTION
    for span in page.spans:
        if span.x0 >= strip_x0 and needle in span.text:
            print(f"p.{page.number:>3} x0={span.x0:.2f} y0={span.y0:.2f} size={span.size:.2f} text={span.text!r}")
