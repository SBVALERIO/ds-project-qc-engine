"""Builds a small synthetic PDF for tests, standing in for a real Revit/
AutoCAD export until we have an actual DS Project Package to test against.

Layout mimics a D-size sheet (24"x36", landscape) with a title block strip
along the right edge, matching the assumptions in qc_engine/titleblock.py.
"""

from __future__ import annotations

import fitz

PAGE_WIDTH = 36 * 72  # 2592 pt
PAGE_HEIGHT = 24 * 72  # 1728 pt


def build_sample_pdf(path: str) -> None:
    doc = fitz.open()

    page1 = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    _insert_titleblock(page1, sheet_number="I-106", sheet_title="RCP - FIRST FLOOR")
    page1.insert_text((200, 200), "WALL LENGHT NOTE: SEE DETAIL 4/A-501", fontsize=10)
    page1.insert_text((200, 230), "CEILING HEIGHT 9'-0\" AFF", fontsize=10)
    page1.insert_text((200, 260), "TOTAL LENGTH OF WALL: 42 FT", fontsize=10)

    page2 = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    _insert_titleblock(page2, sheet_number="I-106.1", sheet_title="RCP - SECOND FLOOR")
    page2.insert_text((200, 200), "CURTAIN LENGHT PER SCHEDULE", fontsize=10)

    doc.save(path)
    doc.close()


def _insert_titleblock(page: "fitz.Page", sheet_number: str, sheet_title: str) -> None:
    x = PAGE_WIDTH * 0.85
    page.insert_text((x, PAGE_HEIGHT - 120), sheet_title, fontsize=14)
    page.insert_text((x, PAGE_HEIGHT - 80), sheet_number, fontsize=28)
