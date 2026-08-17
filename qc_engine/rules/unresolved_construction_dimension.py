"""Demo/construction/reinforcement notes missing their dimension.

The full rule DS wants — "every dimension exists wherever an element is
demolished, constructed or reinforced" — really asks whether every
changed element on the plan has a cote next to it, which means knowing
*which drawn lines* are new/demo/reinforced. That's a linetype/color
classification problem in the vector geometry, not a text problem, and
is out of scope for this pass (see the revision-cloud detour — same
category of "needs the vision layer" work).

What text extraction alone can catch reliably: a note that already uses
one of these action words but leaves the dimension itself as "TBD"
instead of a resolved number — DS does this in practice (e.g.
"REINFORCEMENT WALLS HEIGHT TBD." on the real CASA@63 Construction Floor
Plan). That's a real, unambiguous, zero-guesswork instance of the same
problem this rule is about, so it's what gets checked here.
"""

from __future__ import annotations

import re

from ..models import Document, Finding, Page, TextSpan
from .base import Rule

ACTION_KEYWORDS = re.compile(r"\b(DEMO|DEMOLISH|REMOVE|REINFORC|NEW WALL)\w*", re.IGNORECASE)
TBD_PATTERN = re.compile(r"\bTBD\b", re.IGNORECASE)


class UnresolvedConstructionDimensionRule(Rule):
    rule_id = "unresolved-construction-dimension"

    def run(self, document: Document) -> list[Finding]:
        findings = []
        for page in document.pages:
            for span in page.spans:
                if ACTION_KEYWORDS.search(span.text) and TBD_PATTERN.search(span.text):
                    findings.append(_finding(page, span))
        return findings


def _finding(page: Page, span: TextSpan) -> Finding:
    return Finding(
        id=0,
        title="Cota não resolvida (TBD) em nota de demolição/construção/reforço",
        sheet=page.label(),
        confidence="Alta",
        evidence="Visual",
        summary=f'{page.label()} tem uma nota de obra sem a cota resolvida: “{span.text}”.',
        expected="Toda cota (altura, linear feet, sqft) de elemento demolido, construído ou reforçado precisa existir e estar calculada — substituir o TBD pelo valor confirmado.",
        locations=[f"{page.label()}: “{span.text}”"],
    )
