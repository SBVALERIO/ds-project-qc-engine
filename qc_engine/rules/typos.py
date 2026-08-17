"""Systemic typo detection (e.g. "LENGHT" instead of "LENGTH").

DS keeps running into the same handful of misspellings across a package
because they get typed once into a legend or note and then copy-pasted
sheet to sheet. This rule flags every occurrence of a known typo anywhere
in the package as a single finding per typo, so the correction task reads
"fix this everywhere" instead of producing one finding per sheet.

KNOWN_TYPOS is intentionally small and explicit rather than a spell-checker:
false positives on legitimate architectural vocabulary (which spell-checkers
are bad at) are worse than missing a typo we haven't seen yet. Add entries
here as DS runs into new recurring mistakes.
"""

from __future__ import annotations

import re
from collections import defaultdict

from ..models import Document, Finding
from .base import Rule

KNOWN_TYPOS: dict[str, str] = {
    "LENGHT": "LENGTH",
    "STRUCCO": "STUCCO",
    "SABIATTO": "SABBIATO",
    "CIELING": "CEILING",
    "RECEPTACAL": "RECEPTACLE",
}


class SystemicTypoRule(Rule):
    rule_id = "systemic-typos"

    def run(self, document: Document) -> list[Finding]:
        findings: list[Finding] = []

        for wrong, right in KNOWN_TYPOS.items():
            pattern = re.compile(rf"\b{re.escape(wrong)}\b", re.IGNORECASE)
            occurrences_by_page: dict[int, list[str]] = defaultdict(list)

            for page in document.pages:
                for span in page.spans:
                    if pattern.search(span.text):
                        occurrences_by_page[page.index].append(span.text)

            if not occurrences_by_page:
                continue

            locations: list[str] = []
            sheets: list[str] = []
            for page_index, texts in occurrences_by_page.items():
                page = document.pages[page_index]
                count = len(texts)
                sample = texts[0]
                occurrence_note = f" ({count} ocorrências)" if count > 1 else ""
                locations.append(f"{page.label()}{occurrence_note}: “{sample}”")
                sheets.append(page.label())

            findings.append(
                Finding(
                    id=0,  # assigned by the engine
                    title=f'Erro de digitação sistêmico: "{wrong}" em vez de "{right}"',
                    sheet=" · ".join(sheets[:3]) + (" · ..." if len(sheets) > 3 else ""),
                    confidence="Menor",
                    evidence="Cross-check",
                    summary=(
                        f'"{wrong}" aparece em {len(occurrences_by_page)} prancha(s) do pacote, '
                        f'sempre no lugar de "{right}".'
                    ),
                    expected=f'Corrigir toda ocorrência de "{wrong}" para "{right}" no pacote.',
                    locations=locations,
                )
            )

        return findings
