import sys

from qc_engine.pdf_ingest import load_document

path = sys.argv[1]
page_number = int(sys.argv[2])
x0 = float(sys.argv[3])
y0 = float(sys.argv[4])
x1 = float(sys.argv[5])
y1 = float(sys.argv[6])

document = load_document(path)
page = document.pages[page_number - 1]
spans = [s for s in page.spans if x0 <= s.x0 <= x1 and y0 <= s.y0 <= y1]
spans.sort(key=lambda s: (round(s.y0), s.x0))
for s in spans:
    print(f"  x0={s.x0:7.1f} y0={s.y0:7.1f} size={s.size:5.1f} {s.text!r}")
