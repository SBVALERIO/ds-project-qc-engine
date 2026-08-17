"""Unresolved ("TBD") finish/spec value in a schedule or legend.

Confirmed against a real DS reviewer's own redlines on a Wall Covering
Schedule: several rows had their FINISH column left as "TBD" instead of a
resolved spec, and every one of those was flagged as needing a decision
before the set could be considered final. This is the general form of
that same check — any standalone "TBD" table-cell value anywhere in the
package — rather than being scoped to one schedule type, since DS uses
the same placeholder convention on Floor/Wall/Ceiling legends alike.

Only an exact "TBD" span counts (a schedule cell holding nothing but that
word). A sentence that merely *contains* "TBD" — e.g. "COLOR TBD -" as a
note fragment — is a softer, more ambiguous signal (could be an
intentional pending-client-decision note rather than a documentation
gap) and is left alone to avoid over-flagging.
"""

from __future__ import annotations

import re

from ..models import Document, Finding, Page, TextSpan
from ..titleblock import TITLEBLOCK_X_FRACTION
from .base import Rule

TBD_PATTERN = re.compile(r"^TBD\.?$", re.IGNORECASE)

CONTEXT_Y_ABOVE = 20  # pt
CONTEXT_X_WINDOW = 350  # pt


class UnresolvedFinishRule(Rule):
    rule_id = "unresolved-finish"

    def run(self, document: Document) -> list[Finding]:
        findings = []
        for page in document.pages:
            strip_x0 = page.width * TITLEBLOCK_X_FRACTION
            for span in page.spans:
                if span.x0 < strip_x0 and TBD_PATTERN.match(span.text.strip()):
                    findings.append(_finding(page, span))
        return findings


def _finding(page: Page, span: TextSpan) -> Finding:
    context = _context(page, span)
    return Finding(
        id=0,
        title="Especificação não resolvida (TBD) em schedule/legenda",
        sheet=page.label(),
        confidence="Média",
        evidence="Schedule",
        summary=f'{page.label()} tem um valor de especificação marcado apenas "TBD": “{context}”.',
        expected="Toda especificação de acabamento/material precisa estar definida antes da emissão final; substituir o TBD pela especificação confirmada.",
        locations=[f"{page.label()}: “{context}”"],
    )


def _context(page: Page, tbd_span: TextSpan) -> str:
    nearby = sorted(
        (
            s
            for s in page.spans
            if tbd_span.y0 - CONTEXT_Y_ABOVE <= s.y0 <= tbd_span.y0
            and abs(s.x0 - tbd_span.x0) <= CONTEXT_X_WINDOW
        ),
        key=lambda s: (round(s.y0), s.x0),
    )
    text = " ".join(s.text for s in nearby)
    return re.sub(r"\s+", " ", text).strip()
