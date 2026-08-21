"""Opens a Project Package PDF and extracts per-page text with coordinates.

Revit/AutoCAD PDF exports keep the drawing text as real vector text (not
rasterized), so PyMuPDF's text extraction is enough to recover every label,
schedule row, tag and note on a sheet along with its position — which is
what the cross-check rules need. Pages that were flattened to an image
(scanned shop drawings, etc.) will come back with an empty `spans` list;
callers should treat that as "needs the vision fallback", not as an error.

DS sheets are portrait mediaboxes (1728x2592 for a 24x36) with a /Rotate of
270 applied for landscape viewing. `get_text("dict")` reports bbox
coordinates in the *unrotated* mediabox space, not in the space `page.rect`
(and everything a human sees) uses — so every bbox is transformed through
`page.rotation_matrix` here. Skipping that step silently breaks every
position-based heuristic (title block region, cross-sheet coordinate
matching) without raising an error, since the numbers still "look like"
valid coordinates.
"""

from __future__ import annotations

from typing import Optional

import fitz  # PyMuPDF

from .models import Document, DocumentOrigin, Page, TextSpan
from .titleblock import annotate_titleblocks


def load_document(path: str, origin: Optional[DocumentOrigin] = None) -> Document:
    with fitz.open(path) as pdf:
        pages = []
        for index in range(pdf.page_count):
            pages.append(_extract_page(pdf, index))
            # MuPDF caches decoded fonts/images per page in a process-wide
            # store that otherwise keeps growing for the life of the
            # document — harmless for the small test PDFs this was built
            # against, but a real architectural package (hundreds of dense
            # CAD sheets) can push a memory-capped host (Render's free
            # 512MB) past its limit and get killed mid-request. We only
            # ever read each page once here, so there's nothing to gain
            # from keeping it cached — evict it immediately.
            fitz.TOOLS.store_shrink(100)
    document = Document(source=path, pages=pages, origin=origin)
    # Needs every page loaded first: telling boilerplate title-block chrome
    # apart from the actual sheet number/title relies on seeing what text
    # repeats identically across the whole package.
    annotate_titleblocks(document)
    return document


def _extract_page(pdf: "fitz.Document", index: int) -> Page:
    fitz_page = pdf[index]
    raw = fitz_page.get_text("dict")
    rotation_matrix = fitz_page.rotation_matrix
    spans: list[TextSpan] = []

    for block in raw.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if not text:
                    continue
                rect = fitz.Rect(span["bbox"]) * rotation_matrix
                spans.append(
                    TextSpan(
                        text=text,
                        x0=rect.x0,
                        y0=rect.y0,
                        x1=rect.x1,
                        y1=rect.y1,
                        size=span.get("size", 0.0),
                        font=span.get("font", ""),
                    )
                )

    return Page(
        index=index,
        number=index + 1,
        width=fitz_page.rect.width,
        height=fitz_page.rect.height,
        spans=spans,
    )
