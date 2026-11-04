"""Per-floor quantity note ("QUANTITIES ABOVE REFER TO THE 2ND FLOOR ONLY").

On multi-floor packages DS splits every legend's quantities by floor and
says so in a note under the table. Real review comments (Hibiscus Project
Package, repeated on several sheets) caught two failures:

1. A note naming the wrong floor — the legend was copied from the other
   floor's sheet ("NOTE: QUANTITIES ABOVE REFER TO 2ND FLOOR ONLY" on a
   FIRST FLOOR sheet). Flagged with "Alta" confidence.
2. A floor sheet whose legend has quantities but no such note, in a
   package that otherwise uses the convention. Only checked when at least
   one sheet already carries the note, so packages that don't follow it
   aren't flooded with findings. Flagged with "Média" confidence.
"""

from __future__ import annotations

import re
from typing import Optional

from ..models import Document, Finding, Page
from .base import Rule
from .text_utils import page_lines

FLOOR_WORDS = {
    "1": r"1ST|FIRST|GROUND",
    "2": r"2ND|SECOND",
    "3": r"3RD|THIRD",
    "4": r"4TH|FOURTH",
}
NOTE_PATTERN = re.compile(r"QUANTIT(Y|IES).{0,40}?REFER\s+TO\s+(THE\s+)?(\w+)\s+FLOOR", re.IGNORECASE)
QUANTITY_PATTERN = re.compile(r"\b\d+(\.\d+)?\s*(SQFT|SF|LF)\b|\bQTY\b", re.IGNORECASE)


def _floor_of(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    for floor, words in FLOOR_WORDS.items():
        if re.search(rf"\b({words})\s+FLOOR\b|\b{floor}F\b", text, re.IGNORECASE):
            return floor
    return None


class FloorQuantityNoteRule(Rule):
    rule_id = "floor-quantity-note"

    def run(self, document: Document) -> list[Finding]:
        findings: list[Finding] = []
        notes_by_page: dict[int, list[tuple[str, Optional[str]]]] = {}
        for page in document.pages:
            for text, _ in page_lines(page):
                match = NOTE_PATTERN.search(text)
                if match:
                    notes_by_page.setdefault(page.index, []).append((text, _floor_of(match.group(3) + " FLOOR")))

        convention_used = bool(notes_by_page)
        floor_pages = [(p, _floor_of(p.sheet_title)) for p in document.pages]
        floors_in_package = {f for _, f in floor_pages if f}

        for page, page_floor in floor_pages:
            if page_floor is None:
                continue
            notes = notes_by_page.get(page.index, [])
            wrong = [text for text, note_floor in notes if note_floor and note_floor != page_floor]
            if wrong:
                findings.append(_wrong_floor(page, page_floor, wrong))
            elif (
                convention_used
                and len(floors_in_package) >= 2
                and not notes
                and any(QUANTITY_PATTERN.search(s.text) for s in page.spans)
            ):
                findings.append(_missing_note(page, page_floor))
        return findings


def _floor_name(floor: str) -> str:
    return {"1": "1ST", "2": "2ND", "3": "3RD"}.get(floor, f"{floor}TH")


def _wrong_floor(page: Page, floor: str, notes: list[str]) -> Finding:
    return Finding(
        id=0,
        title="Nota de quantidades refere-se ao andar errado",
        sheet=page.label(),
        confidence="Alta",
        evidence="Cross-check",
        summary=(
            f"A prancha é do {_floor_name(floor)} FLOOR, mas a nota da legenda diz que as quantidades "
            "são de outro andar (provável legenda copiada da outra prancha)."
        ),
        expected=(
            f'Revisar as quantidades para listar só itens do {_floor_name(floor)} FLOOR e corrigir a nota: '
            f'"NOTE: ALL QUANTITIES ABOVE REFER TO THE {_floor_name(floor)} FLOOR ONLY."'
        ),
        locations=[f"{page.label()}: “{text}”" for text in notes],
    )


def _missing_note(page: Page, floor: str) -> Finding:
    return Finding(
        id=0,
        title="Legenda com quantidades sem nota de andar",
        sheet=page.label(),
        confidence="Média",
        evidence="Cross-check",
        summary=(
            "O pacote separa quantidades por andar, mas esta prancha tem quantidades na legenda "
            "sem a nota dizendo a qual andar elas se referem."
        ),
        expected=(
            f'Adicionar abaixo da legenda: "NOTE: ALL QUANTITIES ABOVE REFER TO THE {_floor_name(floor)} FLOOR ONLY." '
            "e conferir que só itens desse andar foram contados."
        ),
        locations=[page.label()],
    )
