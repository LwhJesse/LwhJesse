#!/usr/bin/env python3
from pathlib import Path
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

STATIC_TAGS = {"defs", "style", "title", "desc", "metadata", "script"}


def local_name(tag: str) -> str:
    return tag.split("}", 1)[-1]


def parse_viewbox_or_size(root):
    view_box = root.get("viewBox")
    if view_box:
        nums = [float(x) for x in view_box.replace(",", " ").split()]
        if len(nums) == 4:
            min_x, min_y, width, height = nums
            return min_x, min_y, width, height

    def parse_num(v):
        if v is None:
            return 0.0
        return float(v.replace("px", "").strip())

    width = parse_num(root.get("width"))
    height = parse_num(root.get("height"))
    return 0.0, 0.0, width, height


def ensure_wrapper(root):
    for child in list(root):
        if local_name(child.tag) == "g" and child.get("id") == "__layout_adjust__":
            return child

    wrapper = ET.Element(f"{{{SVG_NS}}}g", {"id": "__layout_adjust__"})

    children = list(root)
    moving = []
    insert_index = None

    for idx, child in enumerate(children):
        if local_name(child.tag) in STATIC_TAGS:
            continue
        moving.append(child)
        if insert_index is None:
            insert_index = idx

    if insert_index is None:
        insert_index = len(children)

    for child in moving:
        root.remove(child)
        wrapper.append(child)

    root.insert(insert_index, wrapper)
    return wrapper


def set_centered_transform(wrapper, min_x, min_y, width, height, sx=1.0, sy=1.0):
    cx = min_x + width / 2.0
    cy = min_y + height / 2.0

    tx = cx * (1.0 - sx)
    ty = cy * (1.0 - sy)

    wrapper.set(
        "transform",
        f"translate({tx:.4f} {ty:.4f}) scale({sx:.6f} {sy:.6f})"
    )


def adjust_svg(path: Path, sx: float, sy: float):
    tree = ET.parse(path)
    root = tree.getroot()

    min_x, min_y, width, height = parse_viewbox_or_size(root)
    wrapper = ensure_wrapper(root)
    set_centered_transform(wrapper, min_x, min_y, width, height, sx=sx, sy=sy)

    tree.write(path, encoding="utf-8", xml_declaration=True)
    print(f"Adjusted {path}  sx={sx:.3f} sy={sy:.3f}")


def main():
    first_cards = [
        Path("profile-summary-card-output/github/0-profile-details.svg"),
        Path("profile-summary-card-output/github_dark/0-profile-details.svg"),
    ]
    second_cards = [
        Path("profile-summary-card-output/github/2-most-commit-language.svg"),
        Path("profile-summary-card-output/github_dark/2-most-commit-language.svg"),
    ]

    missing = [str(p) for p in first_cards + second_cards if not p.exists()]
    if missing:
        raise SystemExit("Missing files:\n" + "\n".join(missing))

    # 第一张：略大一点，重点是纵向稍高一点
    for p in first_cards:
        adjust_svg(p, sx=1.000, sy=1.140)

    # 第二张：整体缩小一点
    for p in second_cards:
        adjust_svg(p, sx=0.720, sy=0.720)


if __name__ == "__main__":
    main()
