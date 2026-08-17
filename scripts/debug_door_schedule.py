import re
import sys

from qc_engine.pdf_ingest import load_document
from qc_engine.schedule_parsing import find_schedule_blocks, row_text

path = sys.argv[1]
page_number = int(sys.argv[2])

HEADER_PATTERN = re.compile(r"^(DOOR|GLASS)\s+SCHEDULE$", re.IGNORECASE)

document = load_document(path)
page = document.pages[page_number - 1]
print(f"p.{page.number} {page.sheet_number} — {page.sheet_title}")

for header, rows in find_schedule_blocks(page, HEADER_PATTERN, min_rows=1):
    print(f"\n== {header.text.strip()!r} (y0={header.y0:.0f}) ==")
    for code, instances in rows.items():
        for spans in instances:
            print(f"  {code:<8} {row_text(spans)}")
