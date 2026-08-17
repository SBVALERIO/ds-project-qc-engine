"""Revision sequence & date consistency, read from each sheet's own
title-block revision table (see qc_engine.revision_table — DS has no
separate master Revision Cloud Schedule; each sheet carries its own).

DS writes the explicit revision number ("R00", "R01", ...) inline in each
row's own description text. Two purely textual checks, no page rendering
or vision needed:

1. The revision numbers on a sheet must be a consecutive run — a gap
   means an intermediate revision was either never issued or never
   recorded, and any revision cloud pointing at the missing number is
   orphaned.
2. Each revision's date must not be earlier than the one before it —
   usually a MM/DD vs DD/MM slip when a revision was logged.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from ..models import Document, Finding, Page
from ..revision_table import RevisionRow, revision_rows
from .base import Rule

REVISION_NUMBER_PATTERN = re.compile(r"\bR(\d{2})\b")

NumberedRow = tuple[int, RevisionRow]


class RevisionSequenceRule(Rule):
    rule_id = "revision-sequence"

    def run(self, document: Document) -> list[Finding]:
        findings: list[Finding] = []
        for page in document.pages:
            numbered = _numbered_rows(revision_rows(page))
            if len(numbered) < 2:
                continue
            findings.extend(_check_sequence(page, numbered))
            findings.extend(_check_dates(page, numbered))
        return findings


def _numbered_rows(rows: list[RevisionRow]) -> list[NumberedRow]:
    result = []
    for row in rows:
        match = REVISION_NUMBER_PATTERN.search(row.description)
        if match:
            result.append((int(match.group(1)), row))
    return result


def _check_sequence(page: Page, numbered: list[NumberedRow]) -> list[Finding]:
    numbers = sorted(n for n, _ in numbered)
    missing = [n for n in range(numbers[0], numbers[-1] + 1) if n not in numbers]
    if not missing:
        return []

    present_labels = ", ".join(f"R{n:02d}" for n in numbers)
    missing_labels = ", ".join(f"R{n:02d}" for n in missing)
    return [
        Finding(
            id=0,
            title=f'Revision Schedule pula revisão em {page.sheet_number or page.label()} ({missing_labels})',
            sheet=page.label(),
            confidence="Alta",
            evidence="Schedule",
            summary=f"A tabela de revisões de {page.label()} lista {present_labels}, sem {missing_labels}.",
            expected="Manter a sequência de revisões rastreável e sem lacunas, ou justificar formalmente a omissão.",
            locations=[f"{page.label()}: {row.date} — {row.description}" for _, row in numbered],
        )
    ]


def _check_dates(page: Page, numbered: list[NumberedRow]) -> list[Finding]:
    findings = []
    prev_n, prev_row = numbered[0]
    prev_date = _parse_date(prev_row.date)
    for n, row in numbered[1:]:
        date = _parse_date(row.date)
        if prev_date is not None and date is not None and date < prev_date:
            findings.append(
                Finding(
                    id=0,
                    title=f'Data de R{n:02d} anterior à revisão anterior em {page.sheet_number or page.label()}',
                    sheet=page.label(),
                    confidence="Alta",
                    evidence="Schedule",
                    summary=(
                        f'Em {page.label()}, R{n:02d} está datada {row.date}, antes de '
                        f'R{prev_n:02d} ({prev_row.date}).'
                    ),
                    expected=(
                        "Uma revisão não pode ter data anterior à revisão que a precede; "
                        "confirmar o formato da data (MM/DD vs DD/MM) ou corrigir a data."
                    ),
                    locations=[f"{page.label()}: R{prev_n:02d} {prev_row.date} → R{n:02d} {row.date}"],
                )
            )
        prev_n, prev_row, prev_date = n, row, date
    return findings


def _parse_date(text: str) -> Optional[datetime]:
    try:
        return datetime.strptime(text, "%m/%d/%Y")
    except ValueError:
        return None
