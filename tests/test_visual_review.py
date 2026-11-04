"""Visual layer: batching, request shape and response parsing, with a fake
Anthropic client (no network)."""

from types import SimpleNamespace

import fitz

from qc_engine.pdf_ingest import load_document
from qc_engine.visual_review import build_batches, load_rules, run_visual_review, visual_review_enabled

PAGE_WIDTH = 36 * 72
PAGE_HEIGHT = 24 * 72


def _build(path):
    doc = fitz.open()
    for number, title in (
        ("I-101", "COVER / INDEX"),
        ("I-106", "RCP - FIRST FLOOR"),
        ("I-107", "LIGHTING - FIRST FLOOR"),
        ("I-110", "OUTLETS - FIRST FLOOR"),
        ("I-206", "RCP - SECOND FLOOR"),
    ):
        page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        page.insert_text((200, 200), "NEW LED COVE", fontsize=10)
        x = PAGE_WIDTH * 0.86
        page.insert_text((x, PAGE_HEIGHT - 120), title, fontsize=14)
        page.insert_text((x, PAGE_HEIGHT - 80), number, fontsize=28)
    doc.save(path)
    doc.close()


class FakeClient:
    def __init__(self, fail_groups=()):
        self.calls = []
        self.messages = self
        self.fail_groups = fail_groups

    def create(self, **kwargs):
        self.calls.append(kwargs)
        intro = kwargs["messages"][0]["content"][0]["text"]
        if any(g in intro for g in self.fail_groups):
            raise RuntimeError("boom")
        findings = []
        if intro.startswith("Grupo: RCP / Lighting / Ceiling / Circuits, 1º andar"):
            findings = [
                {
                    "rule_id": "C01",
                    "title": "Sconce removida no RCP ainda aparece no Lighting",
                    "pages": [2, 3],
                    "confidence": "Média",
                    "found": "Sconce S2 aparece no Lighting (p. 3) mas não no RCP (p. 2).",
                    "expected": "Remover do Lighting ou voltar no RCP.",
                },
                {"rule_id": "ZZ99", "title": "inventada", "pages": [2], "confidence": "Média", "found": "x", "expected": "y"},
            ]
        block = SimpleNamespace(type="tool_use", name="report_findings", input={"findings": findings})
        return SimpleNamespace(content=[block])


def test_batches_group_by_discipline_and_floor(tmp_path):
    path = tmp_path / "pkg.pdf"
    _build(str(path))
    document = load_document(str(path))
    batches = {(g, f): [p.number for p in pages] for g, f, pages in build_batches(document)}
    assert batches[("rcp", "1")] == [2, 3]
    assert batches[("outlets", "1")] == [4]
    assert batches[("rcp", "2")] == [5]
    assert not any(g == "index" for g, _ in batches)


def test_findings_parsed_and_unknown_rules_dropped(tmp_path):
    path = tmp_path / "pkg.pdf"
    _build(str(path))
    document = load_document(str(path))
    client = FakeClient()
    findings = run_visual_review(str(path), document, client=client, max_workers=1)

    assert len(client.calls) == 3
    assert len(findings) == 1
    f = findings[0]
    assert f.evidence == "Visual" and f.confidence == "Média"
    assert "I-106" in f.sheet and "I-107" in f.sheet
    assert f.code_reference.startswith("Regra C01")
    first = client.calls[0]["messages"][0]["content"]
    assert any(part["type"] == "image" for part in first)


def test_api_failure_reported_without_losing_other_groups(tmp_path):
    path = tmp_path / "pkg.pdf"
    _build(str(path))
    document = load_document(str(path))
    findings = run_visual_review(str(path), document, client=FakeClient(fail_groups=("Outlets",)), max_workers=1)
    titles = [f.title for f in findings]
    assert "Revisão visual incompleta" in titles
    assert any("Sconce" in t for t in titles)


def test_rules_catalog_excludes_deterministic_ones():
    ids = {r["id"] for r in load_rules()}
    assert "P01" not in ids and "D07" not in ids
    assert "C01" in ids and "E01" in ids
    assert len(ids) == 71


def test_enable_switch(monkeypatch):
    monkeypatch.delenv("QC_VISUAL_RULES", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert visual_review_enabled(None) is False
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert visual_review_enabled(None) is True
    monkeypatch.setenv("QC_VISUAL_RULES", "off")
    assert visual_review_enabled(None) is False
    assert visual_review_enabled(True) is True
