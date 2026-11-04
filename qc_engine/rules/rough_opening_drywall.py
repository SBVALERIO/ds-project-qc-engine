""""ROUGH OPENING" described as drywall-to-drywall.

DS's convention (confirmed in a reviewer comment on the Height Res /
Dell Anno shop drawings): ROUGH OPENING is measured framing to framing
(2x4 to 2x4), never drywall. Writing "drywall" next to it caused a real
dimension mix-up between the GC and the millworker, so the word must not
appear in a rough-opening note. A finished dimension belongs under
FINISHED OPENING instead.
"""

from __future__ import annotations

import re

from ..models import Document, Finding
from .base import Rule
from .text_utils import page_lines, summarize_sheets

ROUGH_OPENING = re.compile(r"\bROUGH\s+OPENING|\bR\.O\.", re.IGNORECASE)
DRYWALL = re.compile(r"\bDRYWALL|\bGYP(SUM)?\b|\bGWB\b", re.IGNORECASE)


class RoughOpeningDrywallRule(Rule):
    rule_id = "rough-opening-drywall"

    def run(self, document: Document) -> list[Finding]:
        locations: list[str] = []
        sheets: list[str] = []
        for page in document.pages:
            for text, _ in page_lines(page):
                if ROUGH_OPENING.search(text) and DRYWALL.search(text):
                    locations.append(f"{page.label()}: “{text}”")
                    sheets.append(page.label())
        if not locations:
            return []
        return [
            Finding(
                id=0,
                title='"ROUGH OPENING" medido em drywall',
                sheet=summarize_sheets(sheets),
                confidence="Alta",
                evidence="Schedule",
                summary=(
                    f"{len(locations)} nota(s) associam ROUGH OPENING a drywall. "
                    "Rough opening é medido madeira a madeira (2x4), não drywall."
                ),
                expected=(
                    'Remover a palavra "drywall" das notas de ROUGH OPENING (medida madeira a madeira). '
                    "Se a medida for de acabamento, chamar de FINISHED OPENING."
                ),
                locations=locations,
            )
        ]
