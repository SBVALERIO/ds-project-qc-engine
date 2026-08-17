"""Door swing/pocket clearance check (34" swing, 32" pocket).

Florida Building Code — Residential (adopting the IRC egress/accessibility
minimums) requires a passage door to be at least 32" clear width, which in
practice means a 34" nominal swing door (or a 32" nominal pocket door,
which loses less to the frame). DS lists every door in a Door/Glass
Schedule with its own code, nominal width ("32\" x 8'") and type, so this
reads the schedule directly instead of trying to measure door leaves off
the plan.

Only door types that are unambiguously a hinged/pocket passage door are
checked (SWING, DOUBLE, INVISIBLE — DS's flush/frameless doors still
swing open, just without visible hinges — and POCKET). A row whose type
text doesn't match any of those is skipped rather than guessed at.

A door serving an AC/mechanical closet is exempt — confirmed against a DS
reviewer's own comment on a real Door Schedule ("por codigo... portas
swing de passagem... precisam ter no minimo 34"... portas de AC nao
contam"): the 34"/32" minimum is about people passing through, not
equipment access.
"""

from __future__ import annotations

import re

from ..models import Document, Finding, Page, TextSpan
from ..schedule_parsing import Rows, find_schedule_blocks, row_text
from .base import Rule

HEADER_PATTERN = re.compile(r"^(DOOR|GLASS)\s+SCHEDULE$", re.IGNORECASE)
WIDTH_PATTERN = re.compile(r'(\d+(?:\.\d+)?)"\s*x\s*\d')

POCKET_MIN_INCHES = 32
SWING_MIN_INCHES = 34

POCKET_PATTERN = re.compile(r"POCKET", re.IGNORECASE)
SWING_CLASS_PATTERN = re.compile(r"SWING|DOUBLE|INVISIBLE", re.IGNORECASE)
AC_ROOM_PATTERN = re.compile(r"\bA/?C\.?\s*\d|\bA/C\b", re.IGNORECASE)


class DoorClearanceRule(Rule):
    rule_id = "door-clearance"

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
    if AC_ROOM_PATTERN.search(text):
        return None  # AC/mechanical closet door — not a passage door
    width_match = WIDTH_PATTERN.search(text)
    if width_match is None:
        return None
    width = float(width_match.group(1))

    # A row can contain a type keyword that actually belongs to the next
    # row (its opening description line sometimes bleeds into this row's
    # tail — see schedule_parsing.find_schedule_blocks). Picking whichever
    # keyword sits closest to the width value keeps that from silently
    # reclassifying a swing door as a pocket door (or vice versa).
    candidates = [
        (m.start(), "pocket", POCKET_MIN_INCHES) for m in POCKET_PATTERN.finditer(text)
    ] + [(m.start(), "swing", SWING_MIN_INCHES) for m in SWING_CLASS_PATTERN.finditer(text)]
    if not candidates:
        return None  # not a recognizable passage-door type — don't guess
    _, door_class, min_width = min(candidates, key=lambda c: abs(c[0] - width_match.start()))

    if width >= min_width:
        return None

    return Finding(
        id=0,
        title=f'Porta {code} abaixo da largura mínima de clearance ({width:g}" < {min_width}")',
        sheet=page.label(),
        confidence="Alta",
        evidence="Schedule",
        summary=(
            f'{header.text.strip()} ({page.label()}) lista a porta {code} com {width:g}" de largura nominal, '
            f'abaixo do mínimo de código para porta {"pocket" if door_class == "pocket" else "swing"} de passagem.'
        ),
        expected=(
            f'Portas {"pocket" if door_class == "pocket" else "swing"} de passagem precisam de no mínimo '
            f'{min_width}" de largura nominal. Revisar a porta {code} ou confirmar que não é uma porta de passagem.'
        ),
        code_reference="2023 Florida Building Code – Residential (2020 NEC/IRC egress e maneuvering clearance).",
        locations=[f"{page.label()} · {header.text.strip()}: “{text}”"],
    )
