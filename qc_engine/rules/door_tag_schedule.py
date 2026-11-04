"""Door tag on a plan with no row in the Door Schedule.

Reviewer comment on a real package (Nook & David Project Package: "porta
D10 faltando na legenda") — a door tagged on the plan but missing from the
Door Schedule leaves the GC with no type, size or finish to price.

The door codes the package actually uses are learned from its own Door
Schedule(s) (so "D1" vs "D-1" vs "D1.A" conventions all work), and only a
standalone plan span in that same code family counts as a tag. If the
package has no Door Schedule at all, nothing is checked.
"""

from __future__ import annotations

import re

from ..models import Document, Finding, Page, TextSpan
from ..schedule_parsing import find_schedule_blocks
from ..titleblock import TITLEBLOCK_X_FRACTION
from .base import Rule
from .text_utils import summarize_sheets

HEADER_PATTERN = re.compile(r"^(DOOR|DOOR\s*(AND|&)\s*GLASS|GLASS)\s+SCHEDULE$", re.IGNORECASE)
# DS symbol-key "LEGEND" boxes use D00 / G00 as a generic placeholder.
GENERIC_CODE = re.compile(r"^[A-Z]{1,3}[-.]?0+$")
BLOCK_HEIGHT = 500  # pt, matches schedule_parsing.DEFAULT_MAX_BLOCK_HEIGHT
BLOCK_WIDTH = 450


def _normalize(code: str) -> str:
    return re.sub(r"[-.\s]", "", code.upper())


class DoorTagScheduleRule(Rule):
    rule_id = "door-tag-schedule"

    def run(self, document: Document) -> list[Finding]:
        schedule_codes: set[str] = set()
        prefixes: set[str] = set()
        schedule_regions: dict[int, list[TextSpan]] = {}
        for page in document.pages:
            for header, rows in find_schedule_blocks(page, HEADER_PATTERN, min_rows=1):
                schedule_regions.setdefault(page.index, []).append(header)
                for code in rows:
                    match = re.match(r"^([A-Z]{1,3})", code)
                    if match is None or GENERIC_CODE.match(code):
                        continue
                    prefixes.add(match.group(1))
                    schedule_codes.add(_normalize(code))
        if not schedule_codes:
            return []

        tag_pattern = re.compile(
            rf"^({'|'.join(sorted(prefixes, key=len, reverse=True))})[-.]?\d{{1,3}}([-.][A-Z0-9]{{1,3}})?$"
        )

        missing: dict[str, list[str]] = {}
        for page in document.pages:
            headers = schedule_regions.get(page.index, [])
            for span in page.spans:
                text = span.text.strip().upper()
                if not tag_pattern.match(text) or GENERIC_CODE.match(text):
                    continue
                if span.x0 >= page.width * TITLEBLOCK_X_FRACTION:
                    continue  # title block strip (revision table etc.)
                if any(_inside(span, h) for h in headers):
                    continue  # the schedule's own code column
                norm = _normalize(text)
                # "D2.A" on the plan is covered by a "D2" schedule row and vice versa.
                base = re.sub(r"[A-Z]+$", "", norm) if re.search(r"\d[A-Z]+$", norm) else norm
                if norm in schedule_codes or base in schedule_codes:
                    continue
                missing.setdefault(text, []).append(page.label())

        if not missing:
            return []

        codes = sorted(missing, key=lambda c: (re.sub(r"\d", "", c), int(re.sub(r"\D", "", c) or 0)))
        sheets = [label for code in codes for label in missing[code]]
        return [
            Finding(
                id=0,
                title=f"Porta(s) em planta sem linha no Door Schedule: {', '.join(codes)}",
                sheet=summarize_sheets(sheets),
                confidence="Alta",
                evidence="Cross-check",
                summary=(
                    f"{len(codes)} tag(s) de porta aparecem em planta mas não existem no Door Schedule, "
                    "então tipo, dimensão e acabamento ficam sem especificação."
                ),
                expected="Adicionar cada porta ao Door Schedule (tipo, dimensão, acabamento, hardware) ou corrigir a tag na planta.",
                locations=[f"{code}: {', '.join(dict.fromkeys(missing[code]))}" for code in codes],
            )
        ]


def _inside(span: TextSpan, header: TextSpan) -> bool:
    return header.y0 <= span.y0 <= header.y0 + BLOCK_HEIGHT and abs(span.x0 - header.x0) < BLOCK_WIDTH
