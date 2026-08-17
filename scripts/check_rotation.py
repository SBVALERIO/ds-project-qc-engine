import sys

import fitz

path = sys.argv[1]
with fitz.open(path) as pdf:
    page = pdf[0]
    print("rotation", page.rotation)
    print("mediabox", page.mediabox)
    print("rect", page.rect)
    print("cropbox", page.cropbox)
    print("transformation matrix", page.rotation_matrix)
