from qc_engine.engine import analyze_document
from qc_engine.pdf_ingest import load_document

from build_sample_pdf import build_sample_pdf


def _load_sample(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    build_sample_pdf(str(pdf_path))
    return load_document(str(pdf_path))


def test_titleblock_detection(tmp_path):
    document = _load_sample(tmp_path)

    assert document.pages[0].sheet_number == "I-106"
    assert document.pages[0].sheet_title == "RCP - FIRST FLOOR"
    assert document.pages[1].sheet_number == "I-106.1"
    assert document.pages[1].sheet_title == "RCP - SECOND FLOOR"


def test_typo_rule_flags_known_typo_once_across_package(tmp_path):
    document = _load_sample(tmp_path)
    findings = analyze_document(document)

    typo_findings = [f for f in findings if "LENGHT" in f.title]
    assert len(typo_findings) == 1, "LENGHT should be reported once, not once per sheet"

    finding = typo_findings[0]
    assert finding.expected == 'Corrigir toda ocorrência de "LENGHT" para "LENGTH" no pacote.'
    assert len(finding.locations) == 2  # occurs on both sheets
    assert any("I-106" in loc and "I-106.1" not in loc for loc in finding.locations)
    assert any("I-106.1" in loc for loc in finding.locations)


def test_correctly_spelled_word_does_not_inflate_typo_count(tmp_path):
    # Page 1 has both "LENGHT" (typo) and "LENGTH" (correct) in separate
    # spans — the word-boundary match must not conflate the two.
    document = _load_sample(tmp_path)
    findings = analyze_document(document)

    typo_finding = next(f for f in findings if "LENGHT" in f.title)
    page_one_location = next(loc for loc in typo_finding.locations if "I-106" in loc and "I-106.1" not in loc)
    assert "(2" not in page_one_location  # only the one "LENGHT" span, not two
