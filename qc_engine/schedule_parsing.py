"""Shared parsing for DS's schedule/legend table layout.

Every DS schedule (Door Schedule, Floor/Wall/Ceiling Finish Legend, ...)
follows the same shape: a heading, then rows keyed by a short code set in
a noticeably larger font than the row's own content. This locates those
blocks and groups each block's spans into rows by code, without assuming
anything about what the row *means* — that's left to the caller (duplicate
code checks, door width checks, etc.).
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Optional

from .models import Page, TextSpan

CODE_PATTERN = re.compile(r"^[A-Z]{0,3}\.?\d{1,3}(\.[A-Z0-9]{1,3})?$")

DEFAULT_MIN_HEADER_SIZE = 7.0
DEFAULT_COLUMN_WIDTH = 450  # pt, how far right of the header a row's text can sit
DEFAULT_MAX_BLOCK_HEIGHT = 500  # pt, caps a block when no next header exists

Rows = dict[str, list[list[TextSpan]]]


def find_schedule_blocks(
    page: Page,
    header_pattern: re.Pattern[str],
    *,
    exclude_pattern: Optional[re.Pattern[str]] = None,
    min_header_size: float = DEFAULT_MIN_HEADER_SIZE,
    column_width: float = DEFAULT_COLUMN_WIDTH,
    max_block_height: float = DEFAULT_MAX_BLOCK_HEIGHT,
    min_rows: int = 2,
) -> list[tuple[TextSpan, Rows]]:
    """Finds every heading on the page matching `header_pattern` and groups
    the text beneath it into code-keyed rows. Headings matching
    `exclude_pattern` still act as a boundary for the block above them but
    don't get their own block returned (DS's generic symbol-key "LEGEND"
    box uses this to stay a boundary without being treated as data).

    `min_rows` guards against mistaking a legend with no real code column
    (Wall/Ceiling Finish Legend, which has no font distinctly larger than
    its own description text) for one — seeing the same code-like pattern
    repeat at least twice is what makes the "largest font in this block is
    the code column" assumption trustworthy. Callers with a header specific
    enough to already be confident a code column exists (e.g. "DOOR
    SCHEDULE") can pass `min_rows=1` to also catch single-row schedules.
    """

    headers = sorted(
        (s for s in page.spans if s.size >= min_header_size and header_pattern.search(s.text.strip())),
        key=lambda s: s.y0,
    )

    blocks = []
    for i, header in enumerate(headers):
        next_y = headers[i + 1].y0 if i + 1 < len(headers) else page.height
        y_end = min(next_y, header.y0 + max_block_height)

        if exclude_pattern is not None and exclude_pattern.match(header.text.strip()):
            continue

        pool = [
            s
            for s in page.spans
            if s is not header and header.y0 < s.y0 < y_end and abs(s.x0 - header.x0) < column_width
        ]
        rows = _group_into_rows(pool, min_rows)
        if rows:
            blocks.append((header, rows))
    return blocks


def _group_into_rows(pool: list[TextSpan], min_rows: int) -> Rows:
    if not pool:
        return {}

    # The code column sits in the single largest font present in the
    # block's own text — distinctly bigger than any row description.
    code_size = max(s.size for s in pool)
    code_spans = sorted(
        (s for s in pool if abs(s.size - code_size) < 0.3 and CODE_PATTERN.match(s.text)),
        key=lambda s: s.y0,
    )
    if len(code_spans) < min_rows:
        return {}

    rows: Rows = defaultdict(list)
    for i, code_span in enumerate(code_spans):
        # DS's row text sometimes starts a point or two above its own code
        # span (text-box vertical centering quirks) — a small tolerance
        # absorbs that without risking the tightest known row spacing
        # (~6pt on the Floor Finish Legend). A row's *opening* multi-line
        # description can still start further above its code than this
        # covers (observed ~5-6pt on the Door Schedule) and lands in the
        # previous row's text instead; that's an accepted imprecision here
        # since it only duplicates descriptive text, not the dimension/
        # type values the rules that consume this actually key off.
        row_start = code_span.y0 - 3
        row_end = code_spans[i + 1].y0 if i + 1 < len(code_spans) else code_span.y0 + 200
        row_spans = sorted(
            (
                s
                for s in pool
                if row_start <= s.y0 < row_end and s is not code_span and s.size < code_size - 0.3
            ),
            key=lambda s: (round(s.y0), s.x0),
        )
        rows[code_span.text].append(row_spans)
    return rows


def row_text(spans: list[TextSpan]) -> str:
    return re.sub(r"\s+", " ", " ".join(s.text for s in spans)).strip()
