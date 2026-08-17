"""Fixture-code quantity vs how many times it's actually placed.

DS's rule #5 ("toda luminária precisa ter posição idêntica entre
RCP/Lighting/Circuits, mais tag de circuito e linha na Fixture Schedule")
really needs the real x/y position of every fixture symbol across three
separate sheets to check properly. Whether that's even possible from the
PDF text layer depends entirely on how the package was authored:

- Revit tags every luminaire instance with its fixture code in the view
  itself, so a schedule quantity (e.g. "LA01 ... 56") can be cross-checked
  against how many times that code's tag actually appears on the
  RCP/Lighting/Circuits plans — that's what this rule does.
- DS's AutoCAD packages don't carry that per-instance tag at all —
  confirmed against two real packages (CASA@63, HASEN), both of which
  describe each fixture type in a legend paragraph with a running
  quantity and no per-instance code on the plan. No vector-geometry
  shortcut reliably recovers this either (tried and rejected — recessed
  light symbols aren't distinguishable from the rest of a sheet's ~30k
  drawing paths without much more sophisticated shape recognition).

So: for `origin="revit"` this rule checks quantity as described above.
For `origin="autocad"`, rather than silently finding nothing (which
reads as "no problems here"), it reports the coverage gap explicitly so
the review record is honest about what wasn't checked — matching how the
product's regulatory-finding flow already handles "can't confirm, say
what's missing" per the front end's stated conventions.
"""

from __future__ import annotations

import re

from ..models import Document, Finding, Page, TextSpan
from ..schedule_parsing import Rows, find_schedule_blocks, row_text
from .base import Rule

HEADER_PATTERN = re.compile(r"FIXTURE SCHEDULE", re.IGNORECASE)
RELEVANT_SHEET_PATTERN = re.compile(r"RCP|LIGHTING|CIRCUIT", re.IGNORECASE)
QUANTITY_PATTERN = re.compile(r"^\d{1,4}$")


class FixtureQuantityRule(Rule):
    rule_id = "fixture-quantity"

    def run(self, document: Document) -> list[Finding]:
        relevant_pages = [
            page
            for page in document.pages
            if page.sheet_title and RELEVANT_SHEET_PATTERN.search(page.sheet_title)
        ]
        if not relevant_pages:
            return []

        blocks = [
            (schedule_page, header, rows)
            for schedule_page in document.pages
            for header, rows in find_schedule_blocks(schedule_page, HEADER_PATTERN)
        ]

        if not blocks:
            if document.origin == "autocad":
                return [_coverage_gap_finding(relevant_pages[0])]
            return []

        findings: list[Finding] = []
        for schedule_page, header, rows in blocks:
            findings.extend(_check_rows(schedule_page, relevant_pages, header, rows))
        return findings


def _check_rows(schedule_page: Page, relevant_pages: list[Page], header: TextSpan, rows: Rows) -> list[Finding]:
    findings = []
    for code, instances in rows.items():
        for spans in instances:
            quantity = _extract_quantity(spans)
            if quantity is None:
                continue

            placed = sum(
                1
                for page in relevant_pages
                if page is not schedule_page
                for span in page.spans
                if span.text.strip() == code
            )

            if placed == quantity:
                continue

            findings.append(
                Finding(
                    id=0,
                    title=f'Quantidade de {code} não bate entre schedule e plantas ({placed} vs {quantity})',
                    sheet=schedule_page.label(),
                    confidence="Média",
                    evidence="Cross-check",
                    summary=(
                        f'{header.text.strip()} ({schedule_page.label()}) declara {quantity} unidade(s) de {code}, '
                        f'mas o código aparece {placed} vez(es) nas pranchas de RCP/Lighting/Circuits.'
                    ),
                    expected=(
                        f'A quantidade de {code} na Fixture Schedule precisa bater com o número de vezes que o '
                        "código aparece marcado nas plantas de RCP, Lighting e Circuits."
                    ),
                    locations=[f"{schedule_page.label()} · {header.text.strip()}: {code} = {quantity} no schedule, {placed} na(s) planta(s)"],
                )
            )
    return findings


def _coverage_gap_finding(first_relevant_page: Page) -> Finding:
    return Finding(
        id=0,
        title="Posição/quantidade de luminária não verificável (pacote AutoCAD)",
        sheet=first_relevant_page.label(),
        confidence="Média",
        evidence="Visual",
        summary=(
            "Este pacote foi identificado como origem AutoCAD, cujas pranchas de RCP/Lighting/Circuits da DS "
            "não estampam um código por luminária — a legenda usa descrição + contagem total, sem tag por "
            "instância. Não é possível verificar automaticamente se a posição e quantidade de cada luminária "
            "coincide entre RCP, Lighting, Circuits e a Fixture Schedule."
        ),
        expected=(
            "Revisar manualmente se a posição de cada luminária é idêntica entre RCP, Lighting e Circuits, "
            "se cada uma tem tag de circuito, e se corresponde a uma linha na Fixture Schedule."
        ),
        locations=[f"{first_relevant_page.label()}: verificação automática não disponível para pacotes AutoCAD"],
    )


def _extract_quantity(spans: list[TextSpan]) -> int | None:
    candidates = [s.text.strip() for s in spans if QUANTITY_PATTERN.match(s.text.strip())]
    if not candidates:
        return None
    return int(candidates[-1])
