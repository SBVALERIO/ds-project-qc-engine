"""Unresolved ("XX SQFT"-style) quantity placeholders left in a schedule.

This is the unambiguous slice of "the same quantity cited in more than one
place must match": a quantity that was never filled in at all can't
possibly match anything, and is safe to flag with no risk of a false
positive — unlike genuinely cross-referencing two *different* filled-in
quantities against each other, which needs a real example of what DS
considers "the same quantity" before it can be built without guessing at
false positives (see conversation).
"""

from __future__ import annotations

import re

from ..models import Document, Finding, Page, TextSpan
from .base import Rule

PLACEHOLDER_PATTERN = re.compile(r"\bXX\s*(SQFT|SF|LF|LINEAR\s+FEET)\b\.?", re.IGNORECASE)

CONTEXT_Y_ABOVE = 40  # pt, how far up to look for the row's description text
CONTEXT_X_WINDOW = 350  # pt, how far sideways the same row's text can sit


class PlaceholderQuantityRule(Rule):
    rule_id = "placeholder-quantities"

    def run(self, document: Document) -> list[Finding]:
        occurrences: list[tuple[Page, TextSpan]] = []
        for page in document.pages:
            for span in page.spans:
                if PLACEHOLDER_PATTERN.search(span.text):
                    occurrences.append((page, span))

        if not occurrences:
            return []

        locations = [f"{page.label()}: “{_context(page, span)}”" for page, span in occurrences]
        sheets = [page.label() for page, _ in occurrences]

        return [
            Finding(
                id=0,
                title='Quantidade não resolvida ("XX") em schedule/legenda',
                sheet=" · ".join(sheets),
                confidence="Alta",
                evidence="Schedule",
                summary=(
                    f"{len(occurrences)} local(is) do pacote ainda usam um placeholder de quantidade "
                    '("XX SQFT" ou equivalente) em vez de um valor calculado.'
                ),
                expected="Substituir todo placeholder de quantidade pelo valor calculado e verificado.",
                locations=locations,
            )
        ]


def _context(page: Page, placeholder: TextSpan) -> str:
    nearby = sorted(
        (
            s
            for s in page.spans
            if placeholder.y0 - CONTEXT_Y_ABOVE <= s.y0 <= placeholder.y0
            and abs(s.x0 - placeholder.x0) <= CONTEXT_X_WINDOW
        ),
        key=lambda s: (round(s.y0), s.x0),
    )
    text = " ".join(s.text for s in nearby)
    return re.sub(r"\s+", " ", text).strip()
