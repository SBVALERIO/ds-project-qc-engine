"""Synthetic PDF exercising the duplicate-schedule-code rule: a Door
Schedule with a genuine duplicate ("D1" used for two different rows) plus
a generic symbol-key "LEGEND" block that intentionally reuses "D00" and
must NOT be flagged.
"""

from __future__ import annotations

import fitz

PAGE_WIDTH = 36 * 72
PAGE_HEIGHT = 24 * 72


def build_schedule_sample_pdf(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)

    page.insert_text((1900, 100), "DOOR SCHEDULE", fontsize=7.4)
    _row(page, y=125, code="D1", description="SWING DOOR PANTRY")
    _row(page, y=155, code="D2", description="POCKET DOOR GYM")
    _row(page, y=185, code="D1", description="DOUBLE DOOR GARAGE")  # duplicate, different desc

    page.insert_text((1900, 230), "LEGEND", fontsize=7.4)
    _row(page, y=255, code="D00", description="SWING DOOR")
    _row(page, y=285, code="D00", description="DOUBLE DOOR")

    doc.save(path)
    doc.close()


def _row(page: "fitz.Page", y: float, code: str, description: str) -> None:
    page.insert_text((1900, y), code, fontsize=12.4)
    page.insert_text((1950, y + 2), description, fontsize=6.2)
