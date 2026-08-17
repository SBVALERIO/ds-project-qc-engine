"""Data models shared by the extraction layer and the rule engine.

`Finding` mirrors the `Finding` type in the existing Next.js front end
(app/page.tsx) field for field, so the API response can be dropped into
the UI without a translation layer.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Confidence = Literal["Alta", "Média", "Menor"]
Evidence = Literal["Schedule", "Visual", "Cross-check"]
FindingStatus = Literal["Pendente", "Corrigido", "Non Applicable"]

# Matches the origin choice from the upload flow ("Project Package —
# Revit" / "— AutoCAD" / "Shop Drawings"). Some rules behave differently
# per origin — e.g. Revit tags every luminaire instance with its fixture
# code (so quantity/position cross-checks are checkable); DS's AutoCAD
# packages don't carry that tag at all, confirmed against two real
# packages, so the same check can't run and should say so instead of
# silently finding nothing.
DocumentOrigin = Literal["revit", "autocad", "shop_drawings"]


class Finding(BaseModel):
    id: int
    title: str
    sheet: str
    confidence: Confidence
    evidence: Evidence
    status: FindingStatus = "Pendente"
    summary: str
    expected: str
    locations: Optional[list[str]] = None
    code_reference: Optional[str] = Field(default=None, alias="codeReference")
    code_url: Optional[str] = Field(default=None, alias="codeUrl")

    model_config = {"populate_by_name": True}


class TextSpan(BaseModel):
    """A single run of text as reported by PyMuPDF, in PDF point coordinates."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    size: float
    font: str


class Page(BaseModel):
    index: int  # 0-based position in the PDF
    number: int  # 1-based, matches "PDF p. N" language used in the UI
    width: float
    height: float
    spans: list[TextSpan]
    sheet_number: Optional[str] = None
    sheet_title: Optional[str] = None

    def full_text(self) -> str:
        return "\n".join(span.text for span in self.spans)

    def label(self) -> str:
        """Human-readable page reference, e.g. "p. 10 · I-106"."""
        if self.sheet_number:
            suffix = f" · {self.sheet_number}"
            if self.sheet_title:
                suffix += f" — {self.sheet_title}"
            return f"p. {self.number}{suffix}"
        return f"p. {self.number}"


class Document(BaseModel):
    source: str
    pages: list[Page]
    origin: Optional[DocumentOrigin] = None

    def all_spans(self):
        for page in self.pages:
            for span in page.spans:
                yield page, span
