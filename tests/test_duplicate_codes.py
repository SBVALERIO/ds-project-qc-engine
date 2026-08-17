from qc_engine.engine import analyze_document
from qc_engine.pdf_ingest import load_document

from build_schedule_sample_pdf import build_schedule_sample_pdf


def _load_sample(tmp_path):
    pdf_path = tmp_path / "schedule_sample.pdf"
    build_schedule_sample_pdf(str(pdf_path))
    return load_document(str(pdf_path))


def test_duplicate_code_in_real_schedule_is_flagged(tmp_path):
    document = _load_sample(tmp_path)
    findings = analyze_document(document)

    dup_findings = [f for f in findings if '"D1"' in f.title]
    assert len(dup_findings) == 1
    assert dup_findings[0].evidence == "Schedule"
    assert len(dup_findings[0].locations) == 2


def test_generic_legend_reuse_is_not_flagged(tmp_path):
    document = _load_sample(tmp_path)
    findings = analyze_document(document)

    assert not any('"D00"' in f.title for f in findings)


def test_unique_codes_are_not_flagged(tmp_path):
    document = _load_sample(tmp_path)
    findings = analyze_document(document)

    assert not any('"D2"' in f.title for f in findings)
