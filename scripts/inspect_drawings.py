import sys

import fitz

path = sys.argv[1]
page_number = int(sys.argv[2])

with fitz.open(path) as pdf:
    page = pdf[page_number - 1]
    drawings = page.get_drawings()
    print(f"p.{page_number}: {len(drawings)} drawing paths")

    by_color = {}
    for d in drawings:
        color = d.get("color")
        stroke = d.get("stroke_opacity")
        key = (color,)
        by_color.setdefault(key, 0)
        by_color[key] += 1

    for key, count in sorted(by_color.items(), key=lambda kv: -kv[1])[:20]:
        print(f"  color={key[0]} count={count}")

    # look for reddish strokes specifically
    red_paths = [d for d in drawings if d.get("color") and d["color"][0] > 0.5 and d["color"][1] < 0.3 and d["color"][2] < 0.3]
    print(f"\n{len(red_paths)} reddish paths")
    for d in red_paths[:10]:
        items = d.get("items", [])
        print(f"  type={d.get('type')} rect={d.get('rect')} n_items={len(items)} item_types={[it[0] for it in items[:8]]}")
