import re
import sys

from qc_engine.pdf_ingest import load_document

path = sys.argv[1]
pattern = re.compile(sys.argv[2], re.IGNORECASE)

document = load_document(path)
for page in document.pages:
    for span in page.spans:
        if pattern.search(span.text):
            print(f"p.{page.number:>3} {page.sheet_number or '???':<10} x0={span.x0:.0f} y0={span.y0:.0f} {span.text!r}")
