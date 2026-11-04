"""Visual cross-sheet review with Claude, for the Trazo-derived rules that
can't be checked from PDF text alone.

Most of what DS reviewers keep flagging on real packages (642 Trazo tasks
and comments across 11 projects, Nov 2026 — see qc_engine/data/
trazo_rules.json and RULES.md) is about whether *related sheets tell the
same story*: an item removed on the RCP but still drawn on Lighting, a
bubble on the plan with no line in the legend, a curtain pocket with no
dimension, a color in the legend that doesn't match the plan. Those are
visual (clouds, hatches, colors, dimension strings) and cross-sheet, so
the deterministic rules in qc_engine/rules can't see them.

This module renders each sheet, groups related sheets (same discipline,
same floor) into one request so the model can compare them side by side,
and asks Claude to check only the catalogued rules for that group. Every
rule the deterministic engine already covers is excluded so the two
layers never report the same thing twice.

Findings come back with evidence="Visual" and never "Alta" confidence: a
rendered D-size sheet at ~1.5k px loses small text, and the prompt tells
the model to stay silent rather than guess when it can't read something.

Turned on by `check_visual_rules=True`, or by default whenever
ANTHROPIC_API_KEY is set (override with QC_VISUAL_RULES=on|off).
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import fitz  # PyMuPDF

from .models import Document, Finding, Page
from .rules.floor_quantity_note import _floor_of

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-5"
MAX_IMAGE_SIDE = 1568  # px — larger images are downscaled by the API anyway
MAX_PAGES_PER_CALL = 5
MAX_TEXT_PER_PAGE = 4000  # chars of extracted text sent alongside each image
MAX_WORKERS = 3
MAX_FINDINGS_PER_CALL = 10

RULES_PATH = Path(__file__).parent / "data" / "trazo_rules.json"

# Sheet title keywords -> rule group. Order matters: first match wins
# ("CEILING" must win over "FLOOR" in "RCP - FIRST FLOOR CEILING").
GROUP_KEYWORDS: list[tuple[str, re.Pattern[str]]] = [
    ("index", re.compile(r"INDEX|COVER", re.I)),
    ("doors", re.compile(r"DOOR|HARDWARE|GLASS\s+SCHEDULE", re.I)),
    ("rcp", re.compile(r"\bRCP\b|REFLECTED|LIGHTING|CEILING|CIRCUIT|SWITCH", re.I)),
    ("outlets", re.compile(r"OUTLET|POWER|ELECTRICAL|RECEPTACLE|\bAV\b", re.I)),
    ("flooring", re.compile(r"FLOORING|FLOOR\s+FINISH|BASEBOARD", re.I)),
    ("plans", re.compile(r"EXISTING|DEMO|PROPOSED|CONSTRUCTION|FLOOR\s+PLAN|LAYOUT|WINDOW|FINISH", re.I)),
]
# Cover/index sheets and anything unclassified (3D, elevations, details)
# carry none of the cross-sheet rules — not worth an API call.
SKIPPED_GROUPS = {"index", "other"}
GROUP_NAMES = {
    "index": "Index / capa",
    "plans": "Original / Proposed / Construction",
    "flooring": "Flooring / Baseboard",
    "rcp": "RCP / Lighting / Ceiling / Circuits",
    "outlets": "Outlets",
    "doors": "Doors / Hardware",
    "other": "Outras pranchas",
}

SYSTEM_PROMPT = """Você é o revisor de QC da Design Solutions (DS), escritório de interiores em Miami, revisando um Project Package (set de pranchas para o GC/Builcore).

Você recebe um grupo de pranchas relacionadas (mesma disciplina, mesmo andar) e uma lista de regras aprendidas com os comentários reais dos revisores da DS. Verifique SOMENTE essas regras, comparando as pranchas entre si e cada prancha com suas próprias legendas e schedules.

Regras de conduta:
- Reporte apenas o que você consegue ver com clareza na imagem ou no texto extraído. Se a resolução não permite ler um texto, cor ou hatch, NÃO reporte.
- Nunca invente códigos, medidas ou itens. Cite exatamente o que aparece.
- Um problema = um achado, na regra mais específica. Não repita o mesmo problema em regras diferentes.
- Confiança "Média" quando o problema está claro; "Menor" quando é provável mas depende de confirmação.
- Escreva título, encontrado e esperado em português, curtos e diretos, no estilo da DS (termos técnicos em inglês como aparecem nas pranchas).
- Se nada violar as regras, chame a ferramenta com uma lista vazia."""

REPORT_TOOL = {
    "name": "report_findings",
    "description": "Reporta as violações das regras encontradas neste grupo de pranchas.",
    "input_schema": {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "maxItems": MAX_FINDINGS_PER_CALL,
                "items": {
                    "type": "object",
                    "properties": {
                        "rule_id": {"type": "string", "description": "ID da regra violada, ex.: C01"},
                        "title": {"type": "string", "description": "Título curto do problema"},
                        "pages": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Números das páginas do PDF (1-based) onde o problema aparece",
                        },
                        "confidence": {"type": "string", "enum": ["Média", "Menor"]},
                        "found": {"type": "string", "description": "O que está no desenho"},
                        "expected": {"type": "string", "description": "O que a regra pede"},
                    },
                    "required": ["rule_id", "title", "pages", "confidence", "found", "expected"],
                },
            }
        },
        "required": ["findings"],
    },
}


@lru_cache(maxsize=1)
def load_rules() -> list[dict[str, Any]]:
    data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    return [r for r in data["regras"] if not r.get("automatizada_por")]


def visual_review_enabled(explicit: Optional[bool]) -> bool:
    if explicit is not None:
        return explicit
    setting = os.environ.get("QC_VISUAL_RULES", "auto").strip().lower()
    if setting in ("on", "1", "true", "yes"):
        return True
    if setting in ("off", "0", "false", "no"):
        return False
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def classify(page: Page) -> str:
    title = page.sheet_title or ""
    for group, pattern in GROUP_KEYWORDS:
        if pattern.search(title):
            return group
    return "other"


def build_batches(document: Document) -> list[tuple[str, Optional[str], list[Page]]]:
    """(group, floor, pages) batches, each small enough for one request.
    Pages of the same group and floor stay together so the model can
    compare e.g. RCP vs Lighting vs Circuits of the 1st floor."""

    buckets: dict[tuple[str, Optional[str]], list[Page]] = {}
    for page in document.pages:
        if not page.spans:
            continue  # flattened/scanned page: nothing reliable to compare
        key = (classify(page), _floor_of(page.sheet_title))
        buckets.setdefault(key, []).append(page)

    batches = []
    for (group, floor), pages in buckets.items():
        if group in SKIPPED_GROUPS:
            continue
        for i in range(0, len(pages), MAX_PAGES_PER_CALL):
            batches.append((group, floor, pages[i : i + MAX_PAGES_PER_CALL]))
    return batches


def rules_for(group: str) -> list[dict[str, Any]]:
    return [r for r in load_rules() if r["grupo"] in (group, "all")]


def render_page(pdf: "fitz.Document", page: Page) -> bytes:
    fitz_page = pdf[page.index]
    rect = fitz_page.rect  # already rotation-corrected
    zoom = MAX_IMAGE_SIDE / max(rect.width, rect.height)
    pixmap = fitz_page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    data = pixmap.tobytes("png")
    del pixmap
    return data


def _rules_text(rules: list[dict[str, Any]]) -> str:
    return "\n".join(f"- {r['id']} [{r['tipo']}]: {r['verificacao']} (origem: {r['origem']})" for r in rules)


def _page_text(page: Page) -> str:
    text = page.full_text()
    return text[:MAX_TEXT_PER_PAGE] + (" [...]" if len(text) > MAX_TEXT_PER_PAGE else "")


def build_request(group: str, floor: Optional[str], pages: list[Page], images: list[bytes]) -> list[dict[str, Any]]:
    floor_label = f", {floor}º andar" if floor else ""
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                f"Grupo: {GROUP_NAMES.get(group, group)}{floor_label}. {len(pages)} prancha(s).\n\n"
                f"Regras a verificar:\n{_rules_text(rules_for(group))}"
            ),
        }
    ]
    for page, image in zip(pages, images):
        content.append({"type": "text", "text": f"Página {page.number} — {page.label()}"})
        content.append(
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(image).decode()},
            }
        )
        content.append({"type": "text", "text": f"Texto extraído da página {page.number}:\n{_page_text(page)}"})
    return [{"role": "user", "content": content}]


def _to_findings(raw: list[dict[str, Any]], document: Document, group: str) -> list[Finding]:
    by_number = {p.number: p for p in document.pages}
    rules = {r["id"]: r for r in load_rules()}
    findings = []
    for item in raw:
        rule = rules.get(str(item.get("rule_id", "")).strip().upper())
        if rule is None:
            continue  # not one of the catalogued rules — drop rather than trust
        pages = [by_number[n] for n in item.get("pages", []) if n in by_number]
        sheets = [p.label() for p in pages] or [GROUP_NAMES.get(group, group)]
        confidence = item.get("confidence") if item.get("confidence") in ("Média", "Menor") else "Menor"
        findings.append(
            Finding(
                id=0,
                title=str(item.get("title", "")).strip() or rule["verificacao"][:80],
                sheet=" · ".join(dict.fromkeys(sheets)),
                confidence=confidence,
                evidence="Visual",
                summary=str(item.get("found", "")).strip(),
                expected=str(item.get("expected", "")).strip() or rule["verificacao"],
                locations=list(dict.fromkeys(sheets)),
                code_reference=f"Regra {rule['id']} (Trazo: {rule['origem']})",
            )
        )
    return findings


def run_visual_review(
    path: str,
    document: Document,
    *,
    client: Any = None,
    model: Optional[str] = None,
    max_workers: int = MAX_WORKERS,
) -> list[Finding]:
    batches = build_batches(document)
    if not batches:
        return []

    if client is None:
        import anthropic  # imported lazily: only needed when the visual layer runs

        client = anthropic.Anthropic()
    model = model or os.environ.get("QC_VISUAL_MODEL", DEFAULT_MODEL)

    # Render up front, one page at a time, then let the API calls run in
    # parallel. PNGs of ~1.5k px are a few hundred KB each — far below the
    # memory a full-resolution render would need on Render's 512MB plan.
    with fitz.open(path) as pdf:
        rendered = [[render_page(pdf, page) for page in pages] for _, _, pages in batches]
        fitz.TOOLS.store_shrink(100)

    def call(i: int) -> list[Finding]:
        group, floor, pages = batches[i]
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=[REPORT_TOOL],
            tool_choice={"type": "tool", "name": "report_findings"},
            messages=build_request(group, floor, pages, rendered[i]),
        )
        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "report_findings":
                return _to_findings(block.input.get("findings", []), document, group)
        return []

    findings: list[Finding] = []
    failed: list[str] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [(batches[i], pool.submit(call, i)) for i in range(len(batches))]
        for (group, floor, pages), future in futures:
            try:
                findings.extend(future.result())
            except Exception as exc:  # network/API errors must not sink the deterministic results
                logger.warning("visual review failed for %s: %s", group, exc)
                failed.extend(p.label() for p in pages)
                errors.append(f"{type(exc).__name__}: {str(exc)[:300]}")

    if failed:
        findings.append(
            Finding(
                id=0,
                title="Revisão visual incompleta",
                sheet=" · ".join(failed[:3]) + (" · ..." if len(failed) > 3 else ""),
                confidence="Menor",
                evidence="Visual",
                summary=(
                    f"A verificação visual (regras do Trazo) não rodou em {len(failed)} prancha(s) por erro na API: "
                    + " | ".join(dict.fromkeys(errors))
                ),
                expected="Rodar a análise de novo. Se persistir, conferir a ANTHROPIC_API_KEY no Render.",
                locations=failed,
            )
        )
    return findings
