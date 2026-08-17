"""Parses each sheet's own title-block revision table (DATE / BY /
DESCRIPTION rows). DS does not keep a separate master "Revision Cloud
Schedule" — confirmed against the real CASA@63 package, which has no such
sheet — each sheet's title block carries its own local revision history,
and a revision cloud on that sheet should correspond to one of those rows.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from .models import Page, TextSpan
from .titleblock import TITLEBLOCK_X_FRACTION

DATE_LABEL_PATTERN = re.compile(r"^DATE:?$", re.IGNORECASE)
BY_LABEL_PATTERN = re.compile(r"^BY:?$", re.IGNORECASE)
DATE_VALUE_PATTERN = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$")


@dataclass
class RevisionRow:
    date: str
    description: str


def revision_rows(page: Page) -> list[RevisionRow]:
    """Every row in this sheet's own revision table, oldest first."""

    strip_x0 = page.width * TITLEBLOCK_X_FRACTION
    strip = [s for s in page.spans if s.x0 >= strip_x0]

    date_label = next((s for s in strip if DATE_LABEL_PATTERN.match(s.text.strip())), None)
    if date_label is None:
        return []
    by_label = next((s for s in strip if BY_LABEL_PATTERN.match(s.text.strip())), None)

    # The title block also shows the sheet's overall issue date elsewhere
    # (e.g. near "SHEET NO:"), in a different x column but the same date
    # format — restricting to spans near the "DATE:" label's own column
    # keeps that from being mistaken for an extra revision row.
    date_spans = sorted(
        (
            s
            for s in strip
            if s.y0 > date_label.y0
            and DATE_VALUE_PATTERN.match(s.text.strip())
            and abs(s.x0 - date_label.x0) < 40
        ),
        key=lambda s: s.y0,
    )
    if not date_spans:
        return []

    # Description text wraps across multiple lines, and the date value
    # doesn't reliably line up with the *first* of those lines — so each
    # description span is assigned to whichever date is vertically nearest
    # to it, rather than to a fixed row-height window (revisions are
    # spaced far enough apart for this to be unambiguous).
    description_x_max = (by_label.x0 if by_label is not None else date_label.x0) - 2
    description_pool = [s for s in strip if s.y0 > date_label.y0 and s.x0 < description_x_max]

    grouped: dict[int, list[TextSpan]] = defaultdict(list)
    for span in description_pool:
        nearest_index = min(range(len(date_spans)), key=lambda i: abs(date_spans[i].y0 - span.y0))
        grouped[nearest_index].append(span)

    rows = []
    for i, date_span in enumerate(date_spans):
        spans = sorted(grouped.get(i, []), key=lambda s: s.y0)
        description = re.sub(r"\s+", " ", " ".join(s.text for s in spans)).strip()
        rows.append(RevisionRow(date=date_span.text.strip(), description=description))
    return rows
