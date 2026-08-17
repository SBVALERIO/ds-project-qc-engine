from qc_engine.engine import analyze_document
from qc_engine.models import Document, Page, TextSpan


def _span(text: str, x0: float, y0: float, size: float = 6.0) -> TextSpan:
    return TextSpan(text=text, x0=x0, y0=y0, x1=x0 + 10, y1=y0 + size, size=size, font="")


def _build_revit_document() -> Document:
    schedule_page = Page(
        index=0,
        number=1,
        width=2592,
        height=1728,
        sheet_title="I-000 INDEX",
        spans=[
            _span("FIXTURE SCHEDULE", 1900, 900, size=7.4),
            _span("LA01", 1900, 920, size=8.2),
            _span("RECESSED LIGHT", 1950, 922),
            _span("03", 2100, 922),
            _span("LA02", 1900, 940, size=8.2),
            _span("WALL SCONCE", 1950, 942),
            _span("01", 2100, 942),
        ],
    )
    lighting_page = Page(
        index=1,
        number=2,
        width=2592,
        height=1728,
        sheet_title="LIGHTING FLOOR PLAN - FIRST FLOOR",
        # LA01 declared as 3 in the schedule but only placed twice here.
        spans=[_span("LA01", 300, 300), _span("LA01", 400, 300), _span("LA02", 500, 300)],
    )
    return Document(source="test", pages=[schedule_page, lighting_page], origin="revit")


def test_revit_fixture_quantity_mismatch_is_flagged():
    findings = analyze_document(_build_revit_document())

    matches = [f for f in findings if "LA01" in f.title]
    assert len(matches) == 1
    assert "2" in matches[0].summary
    assert "3" in matches[0].summary


def test_revit_fixture_quantity_match_is_not_flagged():
    findings = analyze_document(_build_revit_document())

    assert not any("LA02" in f.title for f in findings)


def test_autocad_coverage_gap_is_reported_when_no_fixture_tags_exist():
    lighting_page = Page(
        index=0,
        number=1,
        width=2592,
        height=1728,
        sheet_title="LIGHTING FLOOR PLAN - FIRST FLOOR",
        spans=[_span("GENERAL NOTE", 300, 300)],
    )
    document = Document(source="test", pages=[lighting_page], origin="autocad")

    findings = analyze_document(document)

    matches = [f for f in findings if "não verificável" in f.title]
    assert len(matches) == 1
    assert matches[0].confidence == "Média"


def test_no_coverage_gap_reported_when_origin_unknown():
    lighting_page = Page(
        index=0,
        number=1,
        width=2592,
        height=1728,
        sheet_title="LIGHTING FLOOR PLAN - FIRST FLOOR",
        spans=[_span("GENERAL NOTE", 300, 300)],
    )
    document = Document(source="test", pages=[lighting_page], origin=None)

    findings = analyze_document(document)

    assert not any("não verificável" in f.title for f in findings)
