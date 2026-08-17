import sys

import fitz

with fitz.open(sys.argv[1]) as pdf:
    print(pdf.page_count)
    page = pdf[0]
    print("size", page.rect.width, page.rect.height, "rotation", page.rotation)
