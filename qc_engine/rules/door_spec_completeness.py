"""Door Schedule row missing its specification columns.

Confirmed against a real Door Schedule: two rows had only WIDTH X HEIGHT
and COUNT filled in — MODEL, ROOM, DOOR FINISH, HINGE & HANDLE/LOCK TYPE,
HARDWARE FINISH and OPENING DIRECTION were all blank. That's exactly the
set of columns DS's own reviewer asked to be explicit, required fields
rather than a free-text Comments column (see rules/door_clearance.py's
docstring for the same reviewer's comment on this schedule).

This doesn't try to check each column individually — DS's column layout
isn't something we've seen enough real examples of yet to map precisely
(see schedule_parsing.py's approach elsewhere, which reads structure
generically rather than by fixed column position). Instead it's a coarser
but reliable signal: once the width/height and a stray count number are
stripped out of a row's text, a real DS door row still carries well over
a hundred characters of model/finish/hardware description — a row with
next to nothing left is missing most or all of its required fields.
"""

from __future__ import annotations

import re

from ..models import Document, Finding, Page, TextSpan
from ..schedule_parsing import Rows, find_schedule_blocks, row_text
from .base import Rule

HEADER_PATTERN = re.compile(r"^DOOR\s+SCHEDULE", re.IGNORECASE)
WIDTH_PATTERN = re.compile(r'\d+(?:\s+\d+/\d+)?"\s*[xX]\s*\d+(?:\s+\d+/\d+)?"')
STRAY_NUMBER_PATTERN = re.compile(r"\b\d{1,3}\b")

MIN_SPEC_CHARS = 20


class DoorSpecCompletenessRule(Rule):
    rule_id = "door-spec-completeness"

    def run(self, document: Document) -> list[Finding]:
        findings: list[Finding] = []
        for page in document.pages:
            for header, rows in find_schedule_blocks(page, HEADER_PATTERN, min_rows=1):
                findings.extend(_check_rows(page, header, rows))
        return findings


def _check_rows(page: Page, header: TextSpan, rows: Rows) -> list[Finding]:
    findings = []
    for code, instances in rows.items():
        for spans in instances:
            finding = _check_row(page, header, code, spans)
            if finding is not None:
                findings.append(finding)
    return findings


def _check_row(page: Page, header: TextSpan, code: str, spans: list[TextSpan]) -> Finding | None:
    text = row_text(spans)
    width_match = WIDTH_PATTERN.search(text)
    if width_match is None:
        return None  # not a real door row (e.g. a legend key) — don't guess

    remaining = WIDTH_PATTERN.sub(" ", text)
    remaining = STRAY_NUMBER_PATTERN.sub(" ", remaining)
    remaining = re.sub(r"\s+", " ", remaining).strip(" .-")

    if len(remaining) >= MIN_SPEC_CHARS:
        return None

    return Finding(
        id=0,
        title=f'Porta {code} sem especificações preenchidas no Door Schedule',
        sheet=page.label(),
        confidence="Alta",
        evidence="Schedule",
        summary=(
            f'{header.text.strip()} ({page.label()}) lista a porta {code} com largura/altura e quantidade, '
            "mas sem modelo, ambiente, acabamento, dobradiça/fechadura, acabamento de ferragem ou direção de abertura."
        ),
        expected=(
            "Toda linha do Door Schedule precisa ter modelo, ambiente, acabamento da porta, "
            "tipo de dobradiça/fechadura, acabamento de ferragem e direção de abertura preenchidos."
        ),
        locations=[f"{page.label()} · {header.text.strip()}: “{text}”"],
    )
