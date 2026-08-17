import fitz

from qc_engine.engine import analyze_document
from qc_engine.pdf_ingest import load_document

PAGE_WIDTH = 36 * 72
PAGE_HEIGHT = 24 * 72


def _build(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((300, 300), "REINFORCEMENT WALLS HEIGHT TBD.", fontsize=6.1)
    page.insert_text((300, 320), "NEW WALL WITH INSULATION - 8'-0\" HEIGHT.", fontsize=6.1)
    doc.save(path)
    doc.close()


def test_unresolved_dimension_note_is_flagged(tmp_path):
    pdf_path = tmp_path / "construction_sample.pdf"
    _build(str(pdf_path))
    document = load_document(str(pdf_path))
    findings = analyze_document(document)

    matches = [f for f in findings if "Cota não resolvida" in f.title]
    assert len(matches) == 1
    assert "REINFORCEMENT" in matches[0].locations[0]


def test_resolved_dimension_note_is_not_flagged(tmp_path):
    pdf_path = tmp_path / "construction_sample.pdf"
    _build(str(pdf_path))
    document = load_document(str(pdf_path))
    findings = analyze_document(document)

    matches = [f for f in findings if "Cota não resolvida" in f.title]
    assert not any("INSULATION" in loc for loc in matches[0].locations)
