import fitz

from qc_engine.engine import analyze_document
from qc_engine.pdf_ingest import load_document

PAGE_WIDTH = 36 * 72
PAGE_HEIGHT = 24 * 72


def _plan_callout(page: "fitz.Page", x: float, y: float, code: str, height_inches: float) -> None:
    page.insert_text((x, y), code, fontsize=8.0)
    page.insert_text((x, y + 12), f'{height_inches:g}" A.F.F.', fontsize=6.0)


def _schedule_row(page: "fitz.Page", y: float, code: str, description: str, height_inches: float) -> None:
    page.insert_text((1900, y), code, fontsize=8.2)
    page.insert_text((1950, y + 2), description, fontsize=6.1)
    page.insert_text((2100, y + 2), f'{height_inches:g}"', fontsize=6.1)


def _build(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)

    # Plan callouts (above the schedule).
    _plan_callout(page, 300, 300, "CE01", 128)  # matches its schedule row
    _plan_callout(page, 500, 300, "CE04", 120)  # matches NEITHER CE04 row (114 or 132)
    _plan_callout(page, 700, 300, "CE02", 100)  # mismatched, but WOOD VENEER-exempt

    # Ceiling Schedule (below/aside the plan).
    page.insert_text((1900, 900), "CEILING SCHEDULE", fontsize=7.4)
    _schedule_row(page, 920, "CE01", "GENERAL EXISTING CEILING", 128)
    _schedule_row(page, 940, "CE04", "CABANA EXISTING CEILING", 114)
    _schedule_row(page, 960, "CE04", "GYM NEW COVE CEILING", 132)
    _schedule_row(page, 980, "CE02", "POWDER WOOD VENEER PANEL", 124)

    doc.save(path)
    doc.close()


def test_plan_height_matching_schedule_is_not_flagged(tmp_path):
    pdf_path = tmp_path / "ceiling_sample.pdf"
    _build(str(pdf_path))
    document = load_document(str(pdf_path))
    findings = analyze_document(document)

    assert not any("CE01" in f.title for f in findings)


def test_plan_height_matching_no_schedule_row_is_flagged(tmp_path):
    pdf_path = tmp_path / "ceiling_sample.pdf"
    _build(str(pdf_path))
    document = load_document(str(pdf_path))
    findings = analyze_document(document)

    matches = [f for f in findings if "Altura de teto" in f.title and "CE04" in f.title]
    assert len(matches) == 1
    assert "120" in matches[0].summary


def test_wood_veneer_finish_is_exempt_from_height_match(tmp_path):
    pdf_path = tmp_path / "ceiling_sample.pdf"
    _build(str(pdf_path))
    document = load_document(str(pdf_path))
    findings = analyze_document(document)

    assert not any("CE02" in f.title for f in findings)
