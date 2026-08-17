"""Renders PDF pages to PNG files: python -m scripts.render_pages <pdf> <out_dir> <start> <end> [zoom]"""

import sys
from pathlib import Path

import fitz

path = sys.argv[1]
out_dir = Path(sys.argv[2])
start = int(sys.argv[3])
end = int(sys.argv[4])
zoom = float(sys.argv[5]) if len(sys.argv) > 5 else 2.0

out_dir.mkdir(parents=True, exist_ok=True)

with fitz.open(path) as pdf:
    for i in range(start - 1, min(end, pdf.page_count)):
        page = pdf[i]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        out_path = out_dir / f"page_{i + 1:03d}.png"
        pix.save(str(out_path))
        print(out_path)
