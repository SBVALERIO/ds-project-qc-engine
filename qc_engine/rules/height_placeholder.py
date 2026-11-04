"""Mounting height left as a placeholder ("H=XX\"") in a note.

DS notes outlets, switches, keypads and pigtails with their mounting
height ("H=48\"") so the GC doesn't have to guess. A recurring review
comment on real packages (Hibiscus Project Package, Height Jobsite Visits:
"indicar altura aqui na nota. H=XX\"") is a note that was dropped in from
the template and never filled in. A placeholder can't be a real height,
so this has no false-positive risk.
"""

from __future__ import annotations

import re

from ..models import Document, Finding
from .base import Rule
from .text_utils import page_lines, summarize_sheets

HEIGHT_PLACEHOLDER = re.compile(r"\bH\s*=\s*(X{2,}|TBD|\?+)\s*\"?", re.IGNORECASE)


class HeightPlaceholderRule(Rule):
    rule_id = "height-placeholder"

    def run(self, document: Document) -> list[Finding]:
        locations: list[str] = []
        sheets: list[str] = []
        for page in document.pages:
            for text, _ in page_lines(page):
                if HEIGHT_PLACEHOLDER.search(text):
                    locations.append(f"{page.label()}: “{text}”")
                    sheets.append(page.label())
        if not locations:
            return []
        return [
            Finding(
                id=0,
                title='Altura de instalação não resolvida ("H=XX") em nota',
                sheet=summarize_sheets(sheets),
                confidence="Alta",
                evidence="Schedule",
                summary=(
                    f"{len(locations)} nota(s) ainda usam um placeholder de altura "
                    '("H=XX\\"" ou equivalente) em vez da altura de instalação.'
                ),
                expected=(
                    'Indicar a altura real em toda nota de outlet/switch/keypad/pigtail (ex.: "H=48\\""), '
                    "de acordo com os shop drawings do fornecedor quando for o caso."
                ),
                locations=locations,
            )
        ]
