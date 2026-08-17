import fitz

from qc_engine.engine import analyze_document
from qc_engine.pdf_ingest import load_document

PAGE_WIDTH = 36 * 72
PAGE_HEIGHT = 24 * 72


def _build(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((1900, 100), "CURTAIN POCKETS - LIMEWASH FINISH.", fontsize=8.4)
    page.insert_text((1900, 112), "XX SQFT.", fontsize=8.4)
    page.insert_text((1900, 140), "GENERAL - REGULAR PAINT.", fontsize=8.4)
    page.insert_text((1900, 152), "1475 SQFT.", fontsize=8.4)
    doc.save(path)
    doc.close()


def test_placeholder_quantity_is_flagged(tmp_path):
    pdf_path = tmp_path / "placeholder_sample.pdf"
    _build(str(pdf_path))
    document = load_document(str(pdf_path))
    findings = analyze_document(document)

    placeholder_findings = [f for f in findings if "XX" in f.title]
    assert len(placeholder_findings) == 1
    assert "CURTAIN POCKETS" in placeholder_findings[0].locations[0]


def test_resolved_quantity_is_not_flagged(tmp_path):
    pdf_path = tmp_path / "placeholder_sample.pdf"
    _build(str(pdf_path))
    document = load_document(str(pdf_path))
    findings = analyze_document(document)

    assert not any("1475" in loc for f in findings for loc in (f.locations or []))
