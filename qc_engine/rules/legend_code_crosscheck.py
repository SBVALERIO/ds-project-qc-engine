"""Finish/ceiling codes on a plan vs. the legend on the same sheet.

DS puts each plan's legend (Floor Finish Legend, Wall Finish Legend,
Ceiling Schedule, Baseboard Legend, ...) on the same sheet as the plan
it describes. Recurring Trazo review comments on real packages caught both
directions of the mismatch:

* a code tagged on the plan with no row in the legend ("nao vejo essa
  bubble na tabela?", "FL15? new balcony floors.");
* a legend row whose code is never used on that sheet's plan — usually a
  leftover from the other floor ("REMOVER ITENS DO 1O ANDAR", "DEIXAR
  APENAS ITENS 1F", "nbao achei esse em planta?").

Only codes with a letter prefix ("FL01", "CE04", "WC-2") are checked — a
bare "01" can't be told apart from any other number on a plan. The
reverse check only runs for a code family that the plan demonstrably tags
as text on that sheet (at least one other code of the family appears),
since some authoring setups draw tags as blocks with no text. Door and
glass schedules are handled by DoorTagScheduleRule; DS's generic symbol
"LEGEND" key is skipped.
"""

from __future__ import annotations

import re
from collections import defaultdict

from ..models import Document, Finding, Page, TextSpan
from ..schedule_parsing import find_schedule_blocks
from ..titleblock import TITLEBLOCK_X_FRACTION
from .base import Rule

HEADER_PATTERN = re.compile(r"(SCHEDULE|LEGEND):?$", re.IGNORECASE)
SKIP_HEADER = re.compile(r"^LEGEND:?$|DOOR|GLASS|REVISION|DRAWING\s+INDEX|SHEET\s+INDEX", re.IGNORECASE)
PREFIXED_CODE = re.compile(r"^([A-Z]{1,3})[-.]?(\d{1,3})([-.][A-Z0-9]{1,3})?$")
GENERIC_CODE = re.compile(r"^[A-Z]{1,3}[-.]?0+$")
BLOCK_HEIGHT = 500
BLOCK_WIDTH = 450


def _norm(code: str) -> str:
    return re.sub(r"[-.\s]", "", code.upper())


class LegendCodeCrossCheckRule(Rule):
    rule_id = "legend-code-crosscheck"

    def run(self, document: Document) -> list[Finding]:
        findings: list[Finding] = []
        for page in document.pages:
            blocks = [
                (h, rows)
                for h, rows in find_schedule_blocks(page, HEADER_PATTERN)
                if not SKIP_HEADER.search(h.text.strip())
            ]
            if not blocks:
                continue

            legend_codes: dict[str, dict[str, str]] = defaultdict(dict)  # prefix -> norm -> header
            for header, rows in blocks:
                for code in rows:
                    m = PREFIXED_CODE.match(code)
                    if m and not GENERIC_CODE.match(code):
                        legend_codes[m.group(1)][_norm(code)] = header.text.strip()
            if not legend_codes:
                continue

            headers = [h for h, _ in blocks]
            tagged: dict[str, set[str]] = defaultdict(set)  # prefix -> norms on plan
            raw: dict[str, str] = {}
            for span in page.spans:
                text = span.text.strip().upper()
                m = PREFIXED_CODE.match(text)
                if not m or m.group(1) not in legend_codes or GENERIC_CODE.match(text):
                    continue
                if span.x0 >= page.width * TITLEBLOCK_X_FRACTION or any(_inside(span, h) for h in headers):
                    continue
                tagged[m.group(1)].add(_norm(text))
                raw.setdefault(_norm(text), text)

            missing_rows = sorted(
                raw[n] for prefix, norms in tagged.items() for n in norms if n not in legend_codes[prefix]
            )
            unused_rows = sorted(
                f"{code} ({hdr})"
                for prefix, codes in legend_codes.items()
                if tagged.get(prefix)
                for code, hdr in codes.items()
                if code not in tagged[prefix]
            )
            if missing_rows:
                findings.append(_missing(page, missing_rows))
            if unused_rows:
                findings.append(_unused(page, unused_rows))
        return findings


def _inside(span: TextSpan, header: TextSpan) -> bool:
    return header.y0 <= span.y0 <= header.y0 + BLOCK_HEIGHT and abs(span.x0 - header.x0) < BLOCK_WIDTH


def _missing(page: Page, codes: list[str]) -> Finding:
    return Finding(
        id=0,
        title=f"Código na planta sem linha na legenda: {', '.join(codes)}",
        sheet=page.label(),
        confidence="Alta",
        evidence="Cross-check",
        summary=f"{len(codes)} código(s) marcados na planta de {page.label()} não aparecem na legenda/schedule da mesma prancha.",
        expected="Adicionar cada código à legenda (especificação + quantidade) ou corrigir a tag na planta.",
        locations=[f"{page.label()}: {c}" for c in codes],
    )


def _unused(page: Page, codes: list[str]) -> Finding:
    return Finding(
        id=0,
        title="Item na legenda sem ocorrência na planta",
        sheet=page.label(),
        confidence="Média",
        evidence="Cross-check",
        summary=(
            f"{len(codes)} linha(s) da legenda de {page.label()} não aparecem em nenhum lugar da planta dessa prancha "
            "(muitas vezes sobra da legenda do outro andar)."
        ),
        expected="Remover da legenda os itens que não existem nesta planta, ou marcar o código onde ele é usado.",
        locations=[f"{page.label()}: {c}" for c in codes],
    )
