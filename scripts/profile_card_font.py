#!/usr/bin/env python3
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

EMBEDDED_FONT_FAMILY = "Lora Profile Cards"
FONT_STACK_CSS = f'"{EMBEDDED_FONT_FAMILY}", Lora, Georgia, serif'
FONT_FILE = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "Lora-ProfileCards.ttf"


@lru_cache(maxsize=1)
def embedded_font_css() -> str:
    data = base64.b64encode(FONT_FILE.read_bytes()).decode("ascii")
    return (
        "@font-face {"
        f'font-family: "{EMBEDDED_FONT_FAMILY}";'
        'src: url("data:font/ttf;base64,'
        f"{data}"
        '") format("truetype");'
        "font-style: normal;"
        "font-weight: 100 700;"
        "}"
    )


def font_style_block(selector: str = "*") -> str:
    return f"{embedded_font_css()}\n{selector} {{ font-family: {FONT_STACK_CSS}; }}"
