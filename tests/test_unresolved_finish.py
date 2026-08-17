import fitz

from qc_engine.engine import analyze_document
from qc_engine.pdf_ingest import load_document

PAGE_WIDTH = 36 * 72
PAGE_HEIGHT = 24 * 72


def _build(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((300, 300), "WC01", fontsize=6.1)
    page.insert_text((350, 300), "GENERAL", fontsize=6.1)
    page.insert_text((420, 300), "LIMEWASH", fontsize=6.1)
    page.insert_text((490, 300), "TBD", fontsize=6.1)

    page.insert_text((300, 320), "WC02", fontsize=6.1)
    page.insert_text((350, 320), "KITCHEN", fontsize=6.1)
    page.insert_text((420, 320), "PORCELAIN TILE 24X48", fontsize=6.1)
    page.insert_text((550, 320), "MICHELANGELO MATTE", fontsize=6.1)

    # "COLOR TBD -" as one span (a note fragment, not a standalone cell)
    # should not be flagged — softer, more ambiguous signal.
    page.insert_text((300, 340), "COLOR TBD -", fontsize=6.1)

    doc.save(path)
    doc.close()


def test_standalone_tbd_cell_is_flagged(tmp_path):
    pdf_path = tmp_path / "finish_sample.pdf"
    _build(str(pdf_path))
    document = load_document(str(pdf_path))
    findings = analyze_document(document)

    matches = [f for f in findings if "Especificação não resolvida" in f.title]
    assert len(matches) == 1
    assert "WC01" in matches[0].locations[0]


def test_resolved_finish_is_not_flagged(tmp_path):
    pdf_path = tmp_path / "finish_sample.pdf"
    _build(str(pdf_path))
    document = load_document(str(pdf_path))
    findings = analyze_document(document)

    matches = [f for f in findings if "Especificação não resolvida" in f.title]
    assert not any("WC02" in loc for loc in matches[0].locations)


def test_tbd_note_fragment_is_not_flagged(tmp_path):
    pdf_path = tmp_path / "finish_sample.pdf"
    _build(str(pdf_path))
    document = load_document(str(pdf_path))
    findings = analyze_document(document)

    matches = [f for f in findings if "Especificação não resolvida" in f.title]
    assert not any("COLOR TBD" in loc for loc in matches[0].locations)
