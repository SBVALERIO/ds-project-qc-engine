"""Prints every page's detected sheet number/title, to sanity-check the
title block heuristic against a real package."""

import sys

from qc_engine.pdf_ingest import load_document

path = sys.argv[1]
document = load_document(path)
for page in document.pages:
    print(f"p.{page.number:>3}  {page.sheet_number or '???':<10} {page.sheet_title or ''}")
