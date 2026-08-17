"""Quick local runner: python -m qc_engine.cli path/to/package.pdf [revit|autocad|shop_drawings]"""

from __future__ import annotations

import json
import sys

from .engine import analyze_pdf


def main() -> None:
    if len(sys.argv) not in (2, 3):
        print("uso: python -m qc_engine.cli caminho/para/pacote.pdf [revit|autocad|shop_drawings]")
        raise SystemExit(1)

    origin = sys.argv[2] if len(sys.argv) == 3 else None
    findings = analyze_pdf(sys.argv[1], origin=origin)
    print(json.dumps([f.model_dump(by_alias=True) for f in findings], indent=2, ensure_ascii=False))
    print(f"\n{len(findings)} finding(s)", file=sys.stderr)


if __name__ == "__main__":
    main()
