"""Small helpers shared by the text-pattern rules added from Trazo review data."""

from __future__ import annotations

import re
from collections import defaultdict

from ..models import Page, TextSpan

LINE_Y_TOLERANCE = 2.5  # pt — spans on the same baseline (one note line)
LINE_X_GAP = 60  # pt — max horizontal gap between spans of the same line


def page_lines(page: Page) -> list[tuple[str, list[TextSpan]]]:
    """Joins spans that sit on the same baseline and close together into
    note lines. AutoCAD often splits one note into several spans (font
    changes, kerning), so a phrase like "ROUGH OPENING (DRYWALL TO DRYWALL)"
    can arrive in pieces."""

    rows: dict[int, list[TextSpan]] = defaultdict(list)
    for span in page.spans:
        rows[round(span.y0 / LINE_Y_TOLERANCE)].append(span)

    lines: list[tuple[str, list[TextSpan]]] = []
    for key in sorted(rows):
        spans = sorted(rows[key], key=lambda s: s.x0)
        current: list[TextSpan] = []
        for span in spans:
            if current and span.x0 - current[-1].x1 > LINE_X_GAP:
                lines.append((_join(current), current))
                current = []
            current.append(span)
        if current:
            lines.append((_join(current), current))
    return lines


def _join(spans: list[TextSpan]) -> str:
    return re.sub(r"\s+", " ", " ".join(s.text for s in spans)).strip()


def summarize_sheets(labels: list[str], limit: int = 3) -> str:
    unique = list(dict.fromkeys(labels))
    return " · ".join(unique[:limit]) + (" · ..." if len(unique) > limit else "")
