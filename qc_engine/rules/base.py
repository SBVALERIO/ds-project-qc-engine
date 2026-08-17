"""Interface every QC rule implements."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Document, Finding


class Rule(ABC):
    """One objective check run against a whole package.

    A rule receives the fully-ingested `Document` (all pages, all text
    spans, title blocks already resolved) and returns zero or more
    `Finding`s. `id` is not set here — the engine assigns sequential ids
    across the whole run so rules can be added/removed without renumbering
    anything by hand.
    """

    #: Short machine name, used for logging and for future rule-exception
    #: lookups (qc_rules / rule_exceptions tables on the front end side).
    rule_id: str

    @abstractmethod
    def run(self, document: Document) -> list[Finding]:
        ...
