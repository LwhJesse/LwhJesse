#!/usr/bin/env python3
import os
import re
import urllib.request
from pathlib import Path

USER = os.environ.get("GITHUB_REPOSITORY_OWNER", "LwhJesse")

CARDS = [
    ("profile-details", "0-profile-details.svg"),
    ("most-commit-language", "2-most-commit-language.svg"),
]

THEMES = ["github", "github_dark"]

BASE = "https://github-profile-summary-cards.vercel.app/api/cards"
FONT_STACK = '\'Segoe UI\', Ubuntu, "Helvetica Neue", Sans-Serif'
TITLE_COLORS = {
    "github": "#0969da",
    "github_dark": "#2f81f7",
}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "LwhJesse-profile-card-fetcher"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def normalize_svg(svg: str, theme: str) -> str:
    title_color = TITLE_COLORS[theme]

    svg = re.sub(
        r"font-family:\s*'Segoe UI', Ubuntu, \"Helvetica Neue\", Sans-Serif",
        f"font-family: {FONT_STACK}",
        svg,
    )

    svg = re.sub(
        r'(<text x="30" y="40" style=")[^"]*(">)',
        rf'\1font-size: 22px; font-weight: 600; fill: {title_color};\2',
        svg,
        count=1,
    )

    return svg


def main():
    for theme in THEMES:
        outdir = Path("profile-summary-card-output") / theme
        outdir.mkdir(parents=True, exist_ok=True)

        for card, filename in CARDS:
            url = f"{BASE}/{card}?username={USER}&theme={theme}"
            data = fetch(url)

            if b"<svg" not in data[:500]:
                raise RuntimeError(f"Unexpected response for {url}")

            path = outdir / filename
            svg = normalize_svg(data.decode("utf-8"), theme)
            path.write_text(svg, encoding="utf-8")
            print(f"wrote {path}")


if __name__ == "__main__":
    main()
