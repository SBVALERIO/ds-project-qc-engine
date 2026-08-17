"""Sheet-number / sheet-title detection from the DS title block.

The DS template packs a lot into the right-edge title block strip: company
letterhead, project name/address, a legal notice, a per-sheet revision
table (date/by/description), a "DESIGN SOLUTIONS TEAM" credit line, scale,
sheet title, sheet number and issue date — several of them in fonts
*larger* than the sheet title itself, so "biggest text in the strip" is not
usable on its own (confirmed against a real DS Project Package PDF).

Two signals, used together:

1. Letterhead/legal boilerplate tends to repeat near-verbatim across most
   sheets. Because these packages are hand-built per sheet in AutoCAD
   (not one shared Revit title block family), the same text can land
   several points apart from sheet to sheet, so the match is on (text,
   coarse position bucket) rather than exact coordinates. This clears out
   the company address, phone, website and legal notice without having to
   hardcode DS's letterhead strings.
2. The literal "SHEET NO:" label is a reliable per-page anchor (unlike
   frequency voting, which can miss for a specific sheet). The sheet
   number is the pattern-matching text just below it; the sheet title is
   the largest remaining text within a window above it, skipping the
   ~50-100pt gap where the "DESIGN SOLUTIONS TEAM" credit line sits.
   Boilerplate filtering runs first so anything the label window happens
   to also catch (the credit line, scale, revision rows) is still cleaned
   up by pattern/date/scale exclusions below.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Optional

from .models import Document, Page, TextSpan

# Right-edge strip where the DS title block lives, as a fraction of page
# width (in rotation-corrected / as-rendered coordinates).
TITLEBLOCK_X_FRACTION = 0.85

SHEET_NUMBER_PATTERN = re.compile(r"^[A-Z]{1,3}-\d{2,4}(\.\d{1,2})?$")
SHEET_NO_LABEL_PATTERN = re.compile(r"^SHEET\s*NO\.?:?$", re.IGNORECASE)
SCALE_PATTERN = re.compile(r"=\s*1['’]|AS\s+INDICATED", re.IGNORECASE)
DATE_PATTERN = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$")
LABEL_PATTERN = re.compile(r":\s*$")  # "SHEET NO:", "DATE:", "BY:", "DESCRIPTION:", ...

# A span only counts as boilerplate once it repeats across a meaningful
# share of the package — small packages (or our synthetic test fixtures)
# won't have enough pages for any single sheet's text to look "repeated".
BOILERPLATE_MIN_PAGES = 3
BOILERPLATE_MIN_FRACTION = 0.5
# ~10pt of sheet-to-sheet jitter observed on identical letterhead text;
# 20pt buckets absorb that. Text is still part of the key, so this doesn't
# risk merging two genuinely different fields.
POSITION_ROUNDING = 20  # points

# Window (in points, measured upward from the "SHEET NO:" label) the sheet
# title is searched in. The gap below TEAM_LINE_MIN_GAP skips the
# "DESIGN SOLUTIONS TEAM" credit line that sits directly above the label.
TEAM_LINE_MIN_GAP = 100
TITLE_ZONE_MAX_GAP = 260
SHEET_NUMBER_MAX_GAP = 80  # the number sits just below the label


def annotate_titleblocks(document: Document) -> None:
    """Fills in `sheet_number` / `sheet_title` on every page, in place."""

    strips = {page.index: _strip_spans(page) for page in document.pages}
    boilerplate = _detect_boilerplate(strips)

    for page in document.pages:
        strip = strips[page.index]
        candidates = [s for s in strip if _position_key(s) not in boilerplate]
        label = _find_label(strip)
        sheet_number = _find_sheet_number(candidates, label)
        sheet_title = _find_sheet_title(candidates, sheet_number, label)
        page.sheet_number = sheet_number
        page.sheet_title = sheet_title


def _strip_spans(page: Page) -> list[TextSpan]:
    strip_x0 = page.width * TITLEBLOCK_X_FRACTION
    spans = [span for span in page.spans if span.x0 >= strip_x0]
    if not spans:
        # Fall back to a bottom band in case a sheet uses a horizontal
        # title block instead of the usual vertical right-edge strip.
        spans = [span for span in page.spans if span.y0 >= page.height * 0.85]
    return spans


def _position_key(span: TextSpan) -> tuple[int, int, str]:
    return (
        round(span.x0 / POSITION_ROUNDING),
        round(span.y0 / POSITION_ROUNDING),
        span.text,
    )


def _detect_boilerplate(strips: dict[int, list[TextSpan]]) -> set[tuple[int, int, str]]:
    if len(strips) < BOILERPLATE_MIN_PAGES:
        return set()

    counts: Counter[tuple[int, int, str]] = Counter()
    for spans in strips.values():
        for span in spans:
            counts[_position_key(span)] += 1

    threshold = max(BOILERPLATE_MIN_PAGES, len(strips) * BOILERPLATE_MIN_FRACTION)
    return {key for key, count in counts.items() if count >= threshold}


def _find_label(strip: list[TextSpan]) -> Optional[TextSpan]:
    matches = [span for span in strip if SHEET_NO_LABEL_PATTERN.match(span.text.strip())]
    return matches[0] if matches else None


def _find_sheet_number(spans: list[TextSpan], label: Optional[TextSpan]) -> Optional[str]:
    candidates = [span for span in spans if SHEET_NUMBER_PATTERN.match(span.text)]
    if label is not None:
        near_label = [s for s in candidates if 0 <= s.y0 - label.y0 <= SHEET_NUMBER_MAX_GAP]
        if near_label:
            candidates = near_label
    if not candidates:
        return None
    return max(candidates, key=lambda span: span.size).text


def _find_sheet_title(
    spans: list[TextSpan], sheet_number: Optional[str], label: Optional[TextSpan]
) -> Optional[str]:
    sheet_number_size = next((s.size for s in spans if s.text == sheet_number), None)

    candidates = [
        span
        for span in spans
        if span.text != sheet_number
        and not SHEET_NUMBER_PATTERN.match(span.text)
        and not SCALE_PATTERN.search(span.text)
        and not DATE_PATTERN.match(span.text)
        and not LABEL_PATTERN.search(span.text)
        and len(span.text) > 2
    ]
    if label is not None:
        title_zone = [
            s for s in candidates if TEAM_LINE_MIN_GAP <= label.y0 - s.y0 <= TITLE_ZONE_MAX_GAP
        ]
        if title_zone:
            candidates = title_zone
    elif sheet_number_size is not None:
        # No label anchor: fall back to "smaller than the sheet number" as
        # a weaker filter (title is always smaller than the sheet number).
        below_number = [s for s in candidates if s.size < sheet_number_size - 0.5]
        candidates = below_number or candidates
    if not candidates:
        return None

    title_size = max(span.size for span in candidates)
    title_spans = sorted(
        (span for span in candidates if abs(span.size - title_size) < 0.3),
        key=lambda span: span.y0,
    )
    return " ".join(span.text for span in title_spans)
