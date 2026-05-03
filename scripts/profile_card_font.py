#!/usr/bin/env python3
from __future__ import annotations

import base64
from pathlib import Path

EMBEDDED_FONT_FAMILY = "Garamond Libre Profile Cards"
FONT_STACK_CSS = f'"{EMBEDDED_FONT_FAMILY}", "Garamond Libre", Georgia, serif'
FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"
FONT_FILES = {
    400: FONT_DIR / "GaramondLibre-ProfileCards-Regular.otf",
    700: FONT_DIR / "GaramondLibre-ProfileCards-Bold.otf",
}


def embedded_font_css() -> str:
    faces = []
    for weight, font_file in FONT_FILES.items():
        data = base64.b64encode(font_file.read_bytes()).decode("ascii")
        faces.append(
            "@font-face {"
            f'font-family: "{EMBEDDED_FONT_FAMILY}";'
            'src: url("data:font/otf;base64,'
            f"{data}"
            '") format("opentype");'
            "font-style: normal;"
            f"font-weight: {weight};"
            "}"
        )
    return "\n".join(faces)


def font_style_block(selector: str = "*") -> str:
    return f"{embedded_font_css()}\n{selector} {{ font-family: {FONT_STACK_CSS}; }}"
