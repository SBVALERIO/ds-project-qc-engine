"""LED supply described as an "outlet" instead of a pigtail.

Millwork LED strips are fed by a pigtail switched from the wall, not by a
receptacle. A reviewer comment on real shop drawings (Height Res / Idelli:
"Outlet = tomada. Se o ponto de LED que vcs precisam eh de PIGTAIL, favor
alterar descricao para PIGTAIL CONNECTION CONTROLLED BY WALL SWITCH")
shows the wrong word makes the GC price and install a receptacle.

Kept narrow: only one note line that ties OUTLET/RECEPTACLE to LED *for*
the LED (e.g. "OUTLET FOR LED", "LED OUTLET"); a legend line listing an
outlet and a separate LED item doesn't match. Confidence is "Média" since
a few vendors genuinely use plug-in drivers.
"""

from __future__ import annotations

import re

from ..models import Document, Finding
from .base import Rule
from .text_utils import page_lines, summarize_sheets

LED_OUTLET = re.compile(
    r"\b(OUTLET|RECEPTACLE)S?\s+(FOR|TO\s+FEED|TO\s+POWER)\s+(THE\s+)?(\w+\s+){0,2}LED\b"
    r"|\bLED\s+(STRIP\s+|TAPE\s+|LIGHT\s+)?(OUTLET|RECEPTACLE)S?\b",
    re.IGNORECASE,
)
PIGTAIL = re.compile(r"PIG\s*TAIL", re.IGNORECASE)


class LedOutletWordingRule(Rule):
    rule_id = "led-outlet-wording"

    def run(self, document: Document) -> list[Finding]:
        locations: list[str] = []
        sheets: list[str] = []
        for page in document.pages:
            for text, _ in page_lines(page):
                if LED_OUTLET.search(text) and not PIGTAIL.search(text):
                    locations.append(f"{page.label()}: “{text}”")
                    sheets.append(page.label())
        if not locations:
            return []
        return [
            Finding(
                id=0,
                title='Alimentação de LED descrita como "outlet" em vez de pigtail',
                sheet=summarize_sheets(sheets),
                confidence="Média",
                evidence="Schedule",
                summary=(
                    f"{len(locations)} nota(s) pedem um outlet/receptacle para alimentar LED. "
                    "Fitas LED de marcenaria são alimentadas por pigtail, não por tomada."
                ),
                expected='Trocar a descrição para "PIGTAIL CONNECTION CONTROLLED BY WALL SWITCH" (confirmar com o fornecedor).',
                locations=locations,
            )
        ]
