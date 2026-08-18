import fitz

from qc_engine.engine import analyze_document
from qc_engine.pdf_ingest import load_document

PAGE_WIDTH = 36 * 72
PAGE_HEIGHT = 24 * 72


def _complete_row(page: "fitz.Page", y: float, code: str) -> None:
    page.insert_text((1900, y), code, fontsize=12.4)
    page.insert_text((1950, y), "FRAMELESS SWING DOOR", fontsize=6.2)
    page.insert_text((2050, y), "POWDER ROOM", fontsize=6.2)
    page.insert_text((2150, y), '34"x96"', fontsize=6.2)
    page.insert_text((1950, y + 10), "MATTE LACQUER ON INTERIOR AND EXTERIOR SIDE WITH LOCK SET", fontsize=6.2)
    page.insert_text((1950, y + 20), "CONCEALED HINGES", fontsize=6.2)
    page.insert_text((2100, y + 20), "GUNMETAL FINISH", fontsize=6.2)
    page.insert_text((2250, y + 20), "INWARDS", fontsize=6.2)
    page.insert_text((2350, y + 20), "1", fontsize=6.2)


def _incomplete_row(page: "fitz.Page", y: float, code: str) -> None:
    page.insert_text((1900, y), code, fontsize=12.4)
    page.insert_text((2150, y), '5 1/2"x2 1/4"', fontsize=6.2)
    page.insert_text((2350, y), "2", fontsize=6.2)


def _build(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((1900, 100), "DOOR SCHEDULE", fontsize=7.4)
    _complete_row(page, 130, "D-1")
    _complete_row(page, 170, "D-2")
    _incomplete_row(page, 210, "D-9")
    doc.save(path)
    doc.close()


def test_incomplete_door_row_is_flagged(tmp_path):
    pdf_path = tmp_path / "door_spec_sample.pdf"
    _build(str(pdf_path))
    document = load_document(str(pdf_path))
    findings = analyze_document(document)

    matches = [f for f in findings if "sem especificações" in f.title and "D-9" in f.title]
    assert len(matches) == 1


def test_complete_door_rows_are_not_flagged(tmp_path):
    pdf_path = tmp_path / "door_spec_sample.pdf"
    _build(str(pdf_path))
    document = load_document(str(pdf_path))
    findings = analyze_document(document)

    matches = [f for f in findings if "sem especificações" in f.title]
    assert not any("D-1" in f.title or "D-2" in f.title for f in matches)
