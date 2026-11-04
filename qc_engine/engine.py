"""Runs the registered rules against an ingested Document."""

from __future__ import annotations

import re
from typing import Optional

from .models import Document, DocumentOrigin, Finding
from .pdf_ingest import load_document
from .rules.base import Rule
from .rules.ceiling_height_match import CeilingHeightMatchRule
from .rules.door_clearance import DoorClearanceRule
from .rules.door_tag_schedule import DoorTagScheduleRule
from .rules.duplicate_codes import DuplicateScheduleCodeRule
from .rules.fixture_quantity import FixtureQuantityRule
from .rules.floor_quantity_note import FloorQuantityNoteRule
from .rules.height_placeholder import HeightPlaceholderRule
from .rules.led_outlet_wording import LedOutletWordingRule
from .rules.legend_code_crosscheck import LegendCodeCrossCheckRule
from .rules.placeholder_quantities import PlaceholderQuantityRule
from .rules.revision_sequence import RevisionSequenceRule
from .rules.rough_opening_drywall import RoughOpeningDrywallRule
from .rules.titleblock_address import TitleblockAddressRule
from .rules.typos import SystemicTypoRule
from .rules.unresolved_construction_dimension import UnresolvedConstructionDimensionRule
from .rules.unresolved_finish import UnresolvedFinishRule
from .visual_review import run_visual_review, visual_review_enabled

RULES: list[Rule] = [
    SystemicTypoRule(),
    DuplicateScheduleCodeRule(),
    PlaceholderQuantityRule(),
    DoorClearanceRule(),
    RevisionSequenceRule(),
    UnresolvedConstructionDimensionRule(),
    CeilingHeightMatchRule(),
    FixtureQuantityRule(),
    # Added from DS reviewers' recurring Trazo comments (Nov 2026).
    DoorTagScheduleRule(),
    LegendCodeCrossCheckRule(),
    HeightPlaceholderRule(),
    RoughOpeningDrywallRule(),
    LedOutletWordingRule(),
    FloorQuantityNoteRule(),
    TitleblockAddressRule(),
]


def analyze_document(document: Document, *, check_tbd_specs: bool = False) -> list[Finding]:
    # A finish/material spec left as "TBD" is normal on an early-stage
    # package and expected to be gone by the time a project is in
    # construction — whether that's worth flagging depends on the
    # project's own stage, not on anything the PDF itself says, so it's
    # the caller's call rather than an always-on rule.
    rules = [*RULES, UnresolvedFinishRule()] if check_tbd_specs else RULES

    findings: list[Finding] = []
    for rule in rules:
        for finding in rule.run(document):
            findings.append(finding)

    for next_id, finding in enumerate(findings, start=1):
        finding.id = next_id

    attach_positions(document, findings)
    return findings


_PAGE_REF = re.compile(r"\bp\. (\d+)")
_QUOTE = re.compile(r"“([^”]+)”")
_CODE = re.compile(r"\b[A-Z]{1,3}[-.]?\d{1,3}(?:\.\d)?\b")


def attach_positions(document: Document, findings: list[Finding]) -> None:
    """Gives each finding a page and, when the quoted text or code can be
    found on that page, a bbox (fractions of the page) so the front end can
    pin it on the rendered sheet — like a reviewer's markup in Trazo."""
    for finding in findings:
        if finding.page is None:
            refs = [finding.sheet, *(finding.locations or [])]
            match = next((m for m in (_PAGE_REF.search(r) for r in refs) if m), None)
            if match:
                finding.page = int(match.group(1))
        if finding.page is None or finding.bbox or not (1 <= finding.page <= len(document.pages)):
            continue
        page = document.pages[finding.page - 1]
        span = _locate(page, finding)
        if span is not None and page.width and page.height:
            finding.bbox = [
                round(max(0.0, span.x0 / page.width), 4),
                round(max(0.0, span.y0 / page.height), 4),
                round(min(1.0, span.x1 / page.width), 4),
                round(min(1.0, span.y1 / page.height), 4),
            ]


def _locate(page, finding: Finding):
    quotes = [q for loc in (finding.locations or []) for q in _QUOTE.findall(loc)]
    for quote in quotes:
        upper = quote.upper()
        parts = sorted(
            (s for s in page.spans if len(s.text.strip()) >= 3 and s.text.strip().upper() in upper),
            key=lambda s: -len(s.text.strip()),
        )
        if parts:
            return parts[0]
    for code in _CODE.findall(finding.title):
        exact = [s for s in page.spans if s.text.strip() == code]
        if exact:
            return exact[0]
    return None


def analyze_pdf(
    path: str,
    origin: Optional[DocumentOrigin] = None,
    *,
    check_tbd_specs: bool = False,
    check_visual_rules: Optional[bool] = None,
) -> list[Finding]:
    document = load_document(path, origin=origin)
    findings = analyze_document(document, check_tbd_specs=check_tbd_specs)

    # Cross-sheet visual rules learned from DS's Trazo review comments (see
    # visual_review.py). None = follow QC_VISUAL_RULES / ANTHROPIC_API_KEY.
    if visual_review_enabled(check_visual_rules):
        findings.extend(run_visual_review(path, document))
        for next_id, finding in enumerate(findings, start=1):
            finding.id = next_id
    return findings
