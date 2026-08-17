"""Duplicate schedule/legend code detection.

DS schedules (Door Schedule, Floor/Wall/Ceiling Finish Legend, ...) key
each row with a short code set in a noticeably larger font than the row's
own description (e.g. "D2" at 12.4pt next to a 5-6pt spec paragraph, or
"01" at 7.8pt next to 6.3pt description text). Plan callouts reference
that code back — the same "D2" legitimately gets stamped on every swing
door of that type. This rule does NOT flag that; it only flags a code
that resolves to more than one *distinct* row inside the same schedule
table, which means whichever plan callout uses it is now ambiguous about
which row it means.

DS also draws a generic "LEGEND" key on door/window sheets explaining
what each symbol looks like (e.g. "D00 — SWING DOOR", "D00 — DOUBLE
DOOR", "D00 — POCKET DOOR"), which intentionally reuses a placeholder
code across rows. That block is excluded by name — it isn't project data.
"""

from __future__ import annotations

import re

from ..models import Document, Finding, Page, TextSpan
from ..schedule_parsing import Rows, find_schedule_blocks, row_text
from .base import Rule

HEADER_PATTERN = re.compile(r"SCHEDULE|LEGEND", re.IGNORECASE)
GENERIC_LEGEND_HEADER = re.compile(r"^LEGEND$", re.IGNORECASE)


class DuplicateScheduleCodeRule(Rule):
    rule_id = "duplicate-schedule-codes"

    def run(self, document: Document) -> list[Finding]:
        findings: list[Finding] = []
        for page in document.pages:
            for header, rows in find_schedule_blocks(
                page, HEADER_PATTERN, exclude_pattern=GENERIC_LEGEND_HEADER
            ):
                findings.extend(_find_duplicates(page, header, rows))
        return findings


def _find_duplicates(page: Page, header: TextSpan, rows: Rows) -> list[Finding]:
    findings = []
    for code, instances in rows.items():
        if len(instances) < 2:
            continue

        descriptions = [row_text(spans) for spans in instances]
        distinct = {_normalize(d) for d in descriptions if d}
        if len(distinct) < 2:
            continue  # same code, same content — not an error

        header_label = header.text.strip()
        findings.append(
            Finding(
                id=0,
                title=f'Código "{code}" duplicado em {header_label.title()}',
                sheet=page.label(),
                confidence="Alta",
                evidence="Schedule",
                summary=(
                    f'O código "{code}" aparece {len(instances)} vezes em {header_label} '
                    f"({page.label()}) com descrições diferentes."
                ),
                expected=(
                    f'Cada código em {header_label} deve identificar uma única linha; '
                    f'renumerar uma das ocorrências de "{code}".'
                ),
                locations=[
                    f"{page.label()} · {header_label}: “{description}”" for description in descriptions if description
                ],
            )
        )
    return findings


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().upper()
