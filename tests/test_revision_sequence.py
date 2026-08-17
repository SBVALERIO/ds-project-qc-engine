import fitz

from qc_engine.engine import analyze_document
from qc_engine.pdf_ingest import load_document

PAGE_WIDTH = 36 * 72
PAGE_HEIGHT = 24 * 72


def _titleblock(page: "fitz.Page", sheet_number: str, revisions: list[tuple[str, str]]) -> None:
    x = PAGE_WIDTH * 0.9
    page.insert_text((x, PAGE_HEIGHT - 700), "SHEET TITLE", fontsize=15.7)
    page.insert_text((x - 80, PAGE_HEIGHT - 500), "DESCRIPTION:", fontsize=7.3)
    page.insert_text((x + 40, PAGE_HEIGHT - 500), "BY:", fontsize=7.3)
    page.insert_text((x + 70, PAGE_HEIGHT - 500), "DATE:", fontsize=7.3)
    for i, (date, description) in enumerate(revisions):
        y = PAGE_HEIGHT - 480 + i * 20
        page.insert_text((x - 80, y), description, fontsize=7.3)
        page.insert_text((x + 40, y), "DS", fontsize=6.8)
        page.insert_text((x + 70, y), date, fontsize=6.2)
    page.insert_text((x, PAGE_HEIGHT - 150), "SHEET NO:", fontsize=9.4)
    page.insert_text((x, PAGE_HEIGHT - 130), sheet_number, fontsize=30.8)
    page.insert_text((x - 80, PAGE_HEIGHT - 80), "7/15/2026", fontsize=11.4)


def _build(path: str) -> None:
    doc = fitz.open()

    gap_page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    _titleblock(gap_page, "I-201", [("02/27/2026", "R00 ORIGINAL DRAWING"), ("05/28/2026", "R02 UPDATED NOTE")])

    inverted_page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    _titleblock(inverted_page, "I-202", [("02/27/2026", "R00 ORIGINAL DRAWING"), ("01/06/2026", "R01 UPDATED NOTE")])

    clean_page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    _titleblock(clean_page, "I-203", [("02/27/2026", "R00 ORIGINAL DRAWING"), ("05/28/2026", "R01 UPDATED NOTE")])

    doc.save(path)
    doc.close()


def test_revision_gap_is_flagged(tmp_path):
    pdf_path = tmp_path / "revision_sample.pdf"
    _build(str(pdf_path))
    document = load_document(str(pdf_path))
    findings = analyze_document(document)

    gap_findings = [f for f in findings if "pula revisão" in f.title and "I-201" in f.title]
    assert len(gap_findings) == 1
    assert "R01" in gap_findings[0].title


def test_inverted_revision_date_is_flagged(tmp_path):
    pdf_path = tmp_path / "revision_sample.pdf"
    _build(str(pdf_path))
    document = load_document(str(pdf_path))
    findings = analyze_document(document)

    date_findings = [f for f in findings if "anterior à revisão anterior" in f.title and "I-202" in f.title]
    assert len(date_findings) == 1


def test_clean_revision_history_is_not_flagged(tmp_path):
    pdf_path = tmp_path / "revision_sample.pdf"
    _build(str(pdf_path))
    document = load_document(str(pdf_path))
    findings = analyze_document(document)

    assert not any("I-203" in f.title for f in findings)
