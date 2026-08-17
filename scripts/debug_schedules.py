import sys

from qc_engine.pdf_ingest import load_document
from qc_engine.rules.duplicate_codes import _schedules_on_page

path = sys.argv[1]
page_number = int(sys.argv[2])

document = load_document(path)
page = document.pages[page_number - 1]
print(f"p.{page.number} {page.sheet_number} — {page.sheet_title}")

for header, rows in _schedules_on_page(page):
    print(f"\n== {header.text.strip()!r} (y0={header.y0:.0f}) ==")
    for code, instances in rows.items():
        for spans in instances:
            desc = " ".join(s.text for s in spans)
            print(f"  {code:<8} {desc}")
