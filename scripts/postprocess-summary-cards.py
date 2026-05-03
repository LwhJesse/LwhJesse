#!/usr/bin/env python3
from pathlib import Path
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

def q(tag: str) -> str:
    return f"{{{SVG_NS}}}{tag}"

TARGETS = {
    "profile-summary-card-output/github/0-profile-details.svg": (1.000, 1.140),
    "profile-summary-card-output/github_dark/0-profile-details.svg": (1.000, 1.140),
    "profile-summary-card-output/github/2-most-commit-language.svg": (0.720, 0.720),
    "profile-summary-card-output/github_dark/2-most-commit-language.svg": (0.720, 0.720),
}

KEEP_TAGS = {"defs", "style", "metadata", "title", "desc"}

def parse_viewbox(root):
    vb = root.get("viewBox")
    if vb:
        vals = [float(x) for x in vb.replace(",", " ").split()]
        if len(vals) == 4:
            return vals
    w = float(root.get("width", "495").replace("px", ""))
    h = float(root.get("height", "195").replace("px", ""))
    return 0.0, 0.0, w, h

def ensure_wrapper(root):
    wrapper = root.find(f"./{q('g')}[@id='postprocess-scale-wrapper']")
    if wrapper is not None:
        return wrapper

    wrapper = ET.Element(q("g"), {"id": "postprocess-scale-wrapper"})
    movable = []

    for child in list(root):
        if not isinstance(child.tag, str):
            continue
        local = child.tag.split("}")[-1]
        if local not in KEEP_TAGS:
            movable.append(child)

    for child in movable:
        root.remove(child)
        wrapper.append(child)

    root.append(wrapper)
    return wrapper

def set_centered_transform(wrapper, min_x, min_y, width, height, sx=1.0, sy=1.0):
    cx = min_x + width / 2.0
    cy = min_y + height / 2.0
    wrapper.set(
        "transform",
        f"translate({cx:.3f} {cy:.3f}) scale({sx:.6f} {sy:.6f}) translate({-cx:.3f} {-cy:.3f})"
    )

def adjust_svg(path: Path, sx: float, sy: float):
    tree = ET.parse(path)
    root = tree.getroot()
    min_x, min_y, width, height = parse_viewbox(root)
    wrapper = ensure_wrapper(root)
    set_centered_transform(wrapper, min_x, min_y, width, height, sx=sx, sy=sy)
    tree.write(path, encoding="utf-8", xml_declaration=True)
    print(f"Adjusted {path}  sx={sx:.3f} sy={sy:.3f}")

def main():
    for name, (sx, sy) in TARGETS.items():
        p = Path(name)
        if not p.exists():
            raise SystemExit(f"Missing file: {p}")
        adjust_svg(p, sx=sx, sy=sy)

if __name__ == "__main__":
    main()
