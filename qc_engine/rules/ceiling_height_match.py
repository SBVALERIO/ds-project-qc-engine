"""Room ceiling-code height vs Ceiling Schedule.

DS's Ceiling/RCP plans stamp a room with its ceiling code and that code's
height directly on the plan (e.g. "CE04" over "132\" A.F.F."), which must
match the same code's HEIGHT FROM LEVEL column in the Ceiling Schedule.

This is deliberately narrower than it sounds: it only flags a plan height
that matches *none* of that code's schedule rows at all. A duplicated
code (the same "CE04" used for a 114" ceiling in one room and a 132"
ceiling in another — confirmed on a real DS reference package, the exact
example DS gave for the duplicate-code rule) is already caught by
DuplicateScheduleCodeRule; disambiguating *which* duplicate a given plan
callout was supposed to mean isn't something text position alone can do
reliably, so this rule and that one are meant to run together rather than
overlap.

A finish that adds real thickness to the ceiling build-up (wood veneer
panels, cladding) legitimately shifts the applied height from the raw
structural height, so schedule rows whose FINISH mentions one of
THICK_FINISH_KEYWORDS are excluded rather than flagged as a mismatch.

Cross-sheet (added from DS's Trazo review comments: "CH geral do apto nao
eh 120, e sim 116", "atualizar todos os ceiling heights de acordo com a
planta PROPOSED... em todas as plantas"): sheets that stamp ceiling codes
but don't carry the Ceiling Schedule themselves (Lighting, Circuits,
Flooring, Proposed) are checked against the package's schedule(s) too, so
a height updated on the RCP but not on the other plans is caught.
"""

from __future__ import annotations

import re

from ..models import Document, Finding, Page, TextSpan
from ..schedule_parsing import Rows, find_schedule_blocks, row_text
from .base import Rule

HEADER_PATTERN = re.compile(r"^CEILING SCHEDULE$", re.IGNORECASE)
HEIGHT_PATTERN = re.compile(r'(\d+(?:\.\d+)?)"')
PLAN_CALLOUT_HEIGHT_PATTERN = re.compile(r'(\d+(?:\.\d+)?)"\s*A\.?F\.?F\.?', re.IGNORECASE)

THICK_FINISH_KEYWORDS = re.compile(r"WOOD VENEER|CLADDING|PANEL", re.IGNORECASE)

# How close a code label and its height must sit on the plan to be read
# as one callout (DS stacks them directly, a few points apart).
CALLOUT_Y_WINDOW = 25
CALLOUT_X_WINDOW = 40


class CeilingHeightMatchRule(Rule):
    rule_id = "ceiling-height-match"

    def run(self, document: Document) -> list[Finding]:
        findings: list[Finding] = []
        package_heights: dict[str, list[tuple[float, bool]]] = {}
        schedule_sheets: list[str] = []
        pages_without_schedule = []
        for page in document.pages:
            schedule_blocks = find_schedule_blocks(page, HEADER_PATTERN)
            if not schedule_blocks:
                pages_without_schedule.append(page)
                continue
            schedule_sheets.append(page.label())
            for header, rows in schedule_blocks:
                heights_by_code = _heights_by_code(rows)
                for code, heights in heights_by_code.items():
                    package_heights.setdefault(code, []).extend(heights)
                findings.extend(_check_plan_callouts(page, header, heights_by_code))

        if package_heights:
            # A header far above the sheet puts every span on these pages
            # in the "plan" zone — they carry no schedule of their own.
            virtual_header = TextSpan(text="CEILING SCHEDULE", x0=0, y0=-1e6, x1=0, y1=-1e6, size=0, font="")
            for page in pages_without_schedule:
                for finding in _check_plan_callouts(page, virtual_header, package_heights):
                    finding.title = finding.title.replace("na planta", "em outra prancha")
                    finding.evidence = "Cross-check"
                    finding.summary += f" (Ceiling Schedule em {', '.join(schedule_sheets)}.)"
                    finding.expected = (
                        "Atualizar a altura desse código em todas as pranchas (RCP, Lighting, Circuits, "
                        "Flooring, Proposed) para bater com o Ceiling Schedule."
                    )
                    findings.append(finding)
        return findings


def _heights_by_code(rows: Rows) -> dict[str, list[tuple[float, bool]]]:
    """code -> [(height, is_thick_finish_exempt), ...] for every schedule row."""
    result: dict[str, list[tuple[float, bool]]] = {}
    for code, instances in rows.items():
        heights = []
        for spans in instances:
            text = row_text(spans)
            match = HEIGHT_PATTERN.search(text)
            if match is None:
                continue
            exempt = bool(THICK_FINISH_KEYWORDS.search(text))
            heights.append((float(match.group(1)), exempt))
        if heights:
            result[code] = heights
    return result


def _check_plan_callouts(page: Page, header: TextSpan, heights_by_code: dict[str, list[tuple[float, bool]]]) -> list[Finding]:
    findings = []
    # Plan callouts live outside the schedule block itself.
    plan_spans = [s for s in page.spans if s.y0 < header.y0 or s.y0 > header.y0 + 500]

    code_spans = [s for s in plan_spans if s.text.strip() in heights_by_code]
    height_spans = [s for s in plan_spans if PLAN_CALLOUT_HEIGHT_PATTERN.match(s.text.strip())]

    for code_span in code_spans:
        nearest_height = min(
            (
                s
                for s in height_spans
                if abs(s.y0 - code_span.y0) <= CALLOUT_Y_WINDOW and abs(s.x0 - code_span.x0) <= CALLOUT_X_WINDOW
            ),
            key=lambda s: abs(s.y0 - code_span.y0),
            default=None,
        )
        if nearest_height is None:
            continue

        code = code_span.text.strip()
        callout_height = float(PLAN_CALLOUT_HEIGHT_PATTERN.match(nearest_height.text.strip()).group(1))
        candidates = heights_by_code[code]

        if any(callout_height == h or exempt for h, exempt in candidates):
            continue

        schedule_heights = ", ".join(f'{h:g}"' for h, _ in candidates)
        findings.append(
            Finding(
                id=0,
                title=f'Altura de teto {code} na planta não bate com o Ceiling Schedule',
                sheet=page.label(),
                confidence="Alta",
                evidence="Cross-check",
                summary=(
                    f'Na planta ({page.label()}), o código {code} está marcado com {callout_height:g}" A.F.F., '
                    f'mas o Ceiling Schedule lista {code} com {schedule_heights}.'
                ),
                expected="A altura marcada na planta para cada código de teto precisa bater com a altura desse mesmo código no Ceiling Schedule.",
                locations=[f'{page.label()}: {code} = {callout_height:g}" na planta vs {schedule_heights} no schedule'],
            )
        )
    return findings
