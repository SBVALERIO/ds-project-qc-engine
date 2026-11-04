"""Project address in the title block differs from the rest of the package.

Real review comment (Nook & David Project Package: "Atualizar nome e
endereco em todas as pranchas"): sheets reused from another project keep
the old project's address in the title block.

Looks only at street-address-like text in the title block strip. An
address present on at least half the sheets is taken as the package's
own (DS's company letterhead address repeats on every sheet too, which is
fine — it's the same everywhere). A sheet that lacks one of those
majority addresses *and* shows a different address instead is flagged.
"""

from __future__ import annotations

import re
from collections import Counter

from ..models import Document, Finding, Page
from ..titleblock import TITLEBLOCK_X_FRACTION
from .base import Rule
from .text_utils import summarize_sheets

STREET = (
    r"ST|STREET|AVE|AVENUE|DR|DRIVE|BLVD|BOULEVARD|WAY|RD|ROAD|LN|LANE|CT|COURT|"
    r"TER|TERRACE|PL|PLACE|CIR|CIRCLE|HWY|PKWY|PARKWAY"
)
ADDRESS_PATTERN = re.compile(rf"^\d{{2,6}}\s+[A-Z0-9 .'-]+?\b({STREET})\b\.?", re.IGNORECASE)
MIN_PAGES = 3


def _addresses(page: Page) -> set[str]:
    strip_x0 = page.width * TITLEBLOCK_X_FRACTION
    found = set()
    for span in page.spans:
        if span.x0 < strip_x0:
            continue
        match = ADDRESS_PATTERN.match(span.text.strip())
        if match:
            found.add(re.sub(r"\s+", " ", match.group(0).upper().rstrip(".")))
    return found


class TitleblockAddressRule(Rule):
    rule_id = "titleblock-address"

    def run(self, document: Document) -> list[Finding]:
        if len(document.pages) < MIN_PAGES:
            return []
        per_page = {page.index: _addresses(page) for page in document.pages}
        counts = Counter(addr for addrs in per_page.values() for addr in addrs)
        majority = {addr for addr, n in counts.items() if n >= len(document.pages) / 2}
        if not majority:
            return []

        flagged: list[tuple[Page, set[str], set[str]]] = []
        for page in document.pages:
            addrs = per_page[page.index]
            missing = majority - addrs
            foreign = addrs - majority
            if missing and foreign:
                flagged.append((page, missing, foreign))
        if not flagged:
            return []

        return [
            Finding(
                id=0,
                title="Endereço do projeto diferente no carimbo de algumas pranchas",
                sheet=summarize_sheets([p.label() for p, _, _ in flagged]),
                confidence="Média",
                evidence="Cross-check",
                summary=(
                    f"{len(flagged)} prancha(s) mostram no carimbo um endereço diferente do usado no resto do pacote "
                    "(provável prancha reaproveitada de outro projeto)."
                ),
                expected="Atualizar nome do cliente e endereço do projeto no carimbo de todas as pranchas.",
                locations=[
                    f"{p.label()}: “{', '.join(sorted(foreign))}” em vez de “{', '.join(sorted(missing))}”"
                    for p, missing, foreign in flagged
                ],
            )
        ]
