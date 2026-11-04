"""Tests for the rules added from DS reviewers' recurring Trazo comments."""

import fitz

from qc_engine.engine import analyze_document
from qc_engine.pdf_ingest import load_document

PAGE_WIDTH = 36 * 72
PAGE_HEIGHT = 24 * 72


def _titleblock(page, number, title, address="4220 LAGUNA STREET"):
    x = PAGE_WIDTH * 0.86
    page.insert_text((x, 300), address, fontsize=8)
    page.insert_text((x, PAGE_HEIGHT - 120), title, fontsize=14)
    page.insert_text((x, PAGE_HEIGHT - 80), number, fontsize=28)


def _findings(tmp_path, build):
    path = tmp_path / "sample.pdf"
    doc = fitz.open()
    build(doc)
    doc.save(str(path))
    doc.close()
    return analyze_document(load_document(str(path)))


def _door_schedule(page):
    page.insert_text((1900, 100), "DOOR SCHEDULE", fontsize=7.4)
    for i, y in ((1, 125), (2, 160), (3, 195)):
        page.insert_text((1900, y), f"D{i}", fontsize=12.4)
        page.insert_text((1950, y + 2), '36" x 8\'', fontsize=6.2)
        page.insert_text((2020, y + 4), "SWING DOOR", fontsize=6.2)


def test_door_tag_missing_from_schedule(tmp_path):
    def build(doc):
        page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        _door_schedule(page)
        for x, tag in ((300, "D1"), (500, "D2"), (700, "D10")):
            page.insert_text((x, 600), tag, fontsize=8)

    findings = [f for f in _findings(tmp_path, build) if "Door Schedule" in f.title and "sem linha" in f.title]
    assert len(findings) == 1
    assert "D10" in findings[0].title
    assert "D1," not in findings[0].title and "D2" not in findings[0].title


def test_door_tags_all_in_schedule_are_clean(tmp_path):
    def build(doc):
        page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        _door_schedule(page)
        page.insert_text((300, 600), "D3", fontsize=8)
        page.insert_text((500, 600), "D00", fontsize=8)  # generic legend placeholder

    assert not any("sem linha" in f.title for f in _findings(tmp_path, build))


def test_height_placeholder_and_rough_opening_and_led_outlet(tmp_path):
    def build(doc):
        page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        page.insert_text((200, 200), 'LIGHT KEYPAD BY AV COMPANY. H=XX"', fontsize=8)
        page.insert_text((200, 240), 'SWITCH H=48"', fontsize=8)
        page.insert_text((200, 280), "ROUGH OPENING (DRYWALL TO DRYWALL) 48-3/16\"", fontsize=8)
        page.insert_text((200, 320), "ROUGH OPENING 2X4 TO 2X4", fontsize=8)
        page.insert_text((200, 360), "OUTLET FOR MILLWORK LED", fontsize=8)
        page.insert_text((200, 400), "PIGTAIL CONNECTION FOR LED CONTROLLED BY WALL SWITCH", fontsize=8)

    findings = _findings(tmp_path, build)
    height = [f for f in findings if "H=XX" in f.title]
    assert len(height) == 1 and len(height[0].locations) == 1

    ro = [f for f in findings if "ROUGH OPENING" in f.title]
    assert len(ro) == 1 and len(ro[0].locations) == 1 and "DRYWALL" in ro[0].locations[0]

    led = [f for f in findings if "pigtail" in f.title]
    assert len(led) == 1 and len(led[0].locations) == 1 and "OUTLET FOR" in led[0].locations[0]


def test_floor_quantity_note_wrong_and_missing(tmp_path):
    def build(doc):
        p1 = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        _titleblock(p1, "I-108", "FLOORING - FIRST FLOOR")
        p1.insert_text((200, 200), "FL01 WOOD FLOORING 1475 SQFT", fontsize=8)
        p1.insert_text((200, 220), "NOTE: ALL QUANTITIES ABOVE REFER TO THE 2ND FLOOR ONLY.", fontsize=8)

        p2 = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        _titleblock(p2, "I-108.1", "FLOORING - SECOND FLOOR")
        p2.insert_text((200, 200), "FL02 PORCELAIN TILE 300 SQFT", fontsize=8)

        p3 = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        _titleblock(p3, "I-109", "RCP - SECOND FLOOR")
        p3.insert_text((200, 200), "CE01 GYP BOARD 300 SQFT", fontsize=8)
        p3.insert_text((200, 220), "NOTE: QUANTITIES ABOVE REFER TO 2ND FLOOR ONLY", fontsize=8)

    findings = _findings(tmp_path, build)
    wrong = [f for f in findings if "andar errado" in f.title]
    assert len(wrong) == 1 and "I-108 " in wrong[0].sheet + " "
    missing = [f for f in findings if "sem nota de andar" in f.title]
    assert len(missing) == 1 and "I-108.1" in missing[0].sheet


def test_titleblock_address_mismatch(tmp_path):
    def build(doc):
        for i in range(4):
            page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
            address = "375 SOUTH HIBISCUS DRIVE" if i == 3 else "4220 LAGUNA STREET"
            _titleblock(page, f"I-10{i}", f"SHEET {i}", address=address)

    findings = [f for f in _findings(tmp_path, build) if "Endereço" in f.title]
    assert len(findings) == 1
    assert "HIBISCUS" in findings[0].locations[0]
    assert "I-103" in findings[0].sheet


def test_new_typos(tmp_path):
    def build(doc):
        page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        page.insert_text((200, 200), "HARWARE FINISH: GUNMETAL", fontsize=8)

    assert any('"HARWARE"' in f.title for f in _findings(tmp_path, build))


def _ceiling_schedule(page, rows, y=900):
    page.insert_text((1900, y), "CEILING SCHEDULE", fontsize=7.4)
    for i, (code, desc, h) in enumerate(rows):
        yy = y + 20 * (i + 1)
        page.insert_text((1900, yy), code, fontsize=8.2)
        page.insert_text((1950, yy + 2), desc, fontsize=6.1)
        page.insert_text((2100, yy + 2), f'{h}"', fontsize=6.1)


def test_ceiling_height_checked_on_sheets_without_schedule(tmp_path):
    def build(doc):
        rcp = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        rcp.insert_text((300, 300), "CE01", fontsize=8)
        rcp.insert_text((300, 312), '116" A.F.F.', fontsize=6)
        _ceiling_schedule(rcp, [("CE01", "GENERAL CEILING", 116), ("CE02", "DROPPED CEILING", 108)])

        lighting = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        lighting.insert_text((300, 300), "CE01", fontsize=8)
        lighting.insert_text((300, 312), '120" A.F.F.', fontsize=6)  # not updated

    findings = [f for f in _findings(tmp_path, build) if "Altura de teto CE01" in f.title]
    assert len(findings) == 1
    assert "p. 2" in findings[0].sheet


def test_legend_code_crosscheck_both_directions(tmp_path):
    def build(doc):
        page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        page.insert_text((1900, 900), "FLOOR FINISH LEGEND", fontsize=7.4)
        for i, (code, desc) in enumerate((("FL01", "WOOD FLOORING"), ("FL02", "PORCELAIN"), ("FL06", "1ST FLOOR STONE"))):
            page.insert_text((1900, 920 + 20 * i), code, fontsize=8.2)
            page.insert_text((1950, 922 + 20 * i), desc, fontsize=6.1)
        page.insert_text((300, 300), "FL01", fontsize=8)
        page.insert_text((500, 300), "FL02", fontsize=8)
        page.insert_text((700, 300), "FL15", fontsize=8)  # not in legend

    findings = _findings(tmp_path, build)
    missing = [f for f in findings if "sem linha na legenda" in f.title]
    assert len(missing) == 1 and "FL15" in missing[0].title
    unused = [f for f in findings if "sem ocorrência na planta" in f.title]
    assert len(unused) == 1 and "FL06" in unused[0].locations[0]
