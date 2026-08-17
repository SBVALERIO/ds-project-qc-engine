import fitz

from qc_engine.engine import analyze_document
from qc_engine.pdf_ingest import load_document

PAGE_WIDTH = 36 * 72
PAGE_HEIGHT = 24 * 72


def _build(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((1900, 100), "DOOR SCHEDULE", fontsize=7.4)

    # D1: a genuine 32" swing door (violates the 34" swing minimum). Its
    # own "SWING DOOR" label sits right after the width, but D2's opening
    # description ("POCKET DOOR") bleeds into D1's row range — mirroring
    # the real CASA@63 Door Schedule layout, where each row's spec text
    # starts a few points above its own code. This must not cause D1 to
    # be misread as a compliant pocket door.
    page.insert_text((1900, 125), "D1", fontsize=12.4)
    page.insert_text((1950, 127), '32" x 8\'', fontsize=6.2)
    page.insert_text((2020, 129), "SWING DOOR", fontsize=6.2)
    page.insert_text((1950, 155), "POCKET DOOR", fontsize=6.2)  # belongs to D2

    page.insert_text((1900, 160), "D2", fontsize=12.4)
    page.insert_text((1950, 162), '34" x 8\'', fontsize=6.2)
    page.insert_text((2020, 164), "SWING DOOR", fontsize=6.2)

    page.insert_text((1900, 195), "D3", fontsize=12.4)
    page.insert_text((1950, 197), '32" x 8\'', fontsize=6.2)
    page.insert_text((2020, 199), "POCKET DOOR", fontsize=6.2)

    # D4: undersized swing door, but it serves an AC/mechanical closet —
    # exempt from the passage-door minimum per DS's own review comment.
    page.insert_text((1900, 230), "D4", fontsize=12.4)
    page.insert_text((1950, 232), '24" x 8\'', fontsize=6.2)
    page.insert_text((2020, 234), "SWING DOOR", fontsize=6.2)
    page.insert_text((1950, 245), "AC.1", fontsize=6.2)

    doc.save(path)
    doc.close()


def test_undersized_swing_door_is_flagged_despite_bleeding_pocket_text(tmp_path):
    pdf_path = tmp_path / "door_sample.pdf"
    _build(str(pdf_path))
    document = load_document(str(pdf_path))
    findings = analyze_document(document)

    d1_findings = [f for f in findings if "Porta D1" in f.title]
    assert len(d1_findings) == 1
    assert '34"' in d1_findings[0].title  # classified as swing (34" min), not pocket


def test_compliant_swing_door_is_not_flagged(tmp_path):
    pdf_path = tmp_path / "door_sample.pdf"
    _build(str(pdf_path))
    document = load_document(str(pdf_path))
    findings = analyze_document(document)

    assert not any("Porta D2" in f.title for f in findings)


def test_compliant_pocket_door_is_not_flagged(tmp_path):
    pdf_path = tmp_path / "door_sample.pdf"
    _build(str(pdf_path))
    document = load_document(str(pdf_path))
    findings = analyze_document(document)

    assert not any("Porta D3" in f.title for f in findings)


def test_undersized_ac_closet_door_is_exempt(tmp_path):
    pdf_path = tmp_path / "door_sample.pdf"
    _build(str(pdf_path))
    document = load_document(str(pdf_path))
    findings = analyze_document(document)

    assert not any("Porta D4" in f.title for f in findings)
