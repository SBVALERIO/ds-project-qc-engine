"""Runs the registered rules against an ingested Document."""

from __future__ import annotations

from typing import Optional

from .models import Document, DocumentOrigin, Finding
from .pdf_ingest import load_document
from .rules.base import Rule
from .rules.ceiling_height_match import CeilingHeightMatchRule
from .rules.door_clearance import DoorClearanceRule
from .rules.duplicate_codes import DuplicateScheduleCodeRule
from .rules.fixture_quantity import FixtureQuantityRule
from .rules.placeholder_quantities import PlaceholderQuantityRule
from .rules.revision_sequence import RevisionSequenceRule
from .rules.typos import SystemicTypoRule
from .rules.unresolved_construction_dimension import UnresolvedConstructionDimensionRule
from .rules.unresolved_finish import UnresolvedFinishRule

RULES: list[Rule] = [
    SystemicTypoRule(),
    DuplicateScheduleCodeRule(),
    PlaceholderQuantityRule(),
    DoorClearanceRule(),
    RevisionSequenceRule(),
    UnresolvedConstructionDimensionRule(),
    CeilingHeightMatchRule(),
    FixtureQuantityRule(),
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

    return findings


def analyze_pdf(path: str, origin: Optional[DocumentOrigin] = None, *, check_tbd_specs: bool = False) -> list[Finding]:
    document = load_document(path, origin=origin)
    return analyze_document(document, check_tbd_specs=check_tbd_specs)
