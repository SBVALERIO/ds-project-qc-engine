import sys

from qc_engine.pdf_ingest import load_document
from qc_engine.revision_table import revision_rows

path = sys.argv[1]
document = load_document(path)

for page in document.pages:
    rows = revision_rows(page)
    print(f"p.{page.number:>3} {page.sheet_number or '???':<10} {len(rows)} revision(s)")
    for row in rows:
        print(f"        {row.date}  {row.description}")
