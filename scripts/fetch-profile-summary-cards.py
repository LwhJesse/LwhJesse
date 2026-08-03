#!/usr/bin/env python3
import os
import re
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

from profile_card_font import EMBEDDED_FONT_FAMILY, font_style_block

USER = os.environ.get("GITHUB_REPOSITORY_OWNER", "LwhJesse")

CARDS = [
    ("profile-details", "0-profile-details.svg"),
    ("most-commit-language", "2-most-commit-language.svg"),
]

THEMES = ["github", "github_dark"]

BASE = "https://github-profile-summary-cards.vercel.app/api/cards"
TITLE_COLORS = {
    "github": "#0969da",
    "github_dark": "#2f81f7",
}


def fetch(url: str, retries: int = 4) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "LwhJesse-profile-card-fetcher"},
    )

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as error:
            last_error = error
            transient = error.code == 429 or error.code >= 500
            if transient and attempt < retries:
                time.sleep(1.5 * attempt)
                continue
            raise RuntimeError(f"request failed: {url}\n{error}") from error
        except (urllib.error.URLError, TimeoutError, ssl.SSLError, ConnectionResetError) as error:
            last_error = error
            if attempt < retries:
                time.sleep(1.5 * attempt)
                continue
            raise RuntimeError(f"request failed: {url}\n{error}") from error

    raise RuntimeError(f"request failed: {url}\n{last_error}")


def normalize_svg(svg: str, theme: str) -> str:
    title_color = TITLE_COLORS[theme]

    svg = re.sub(
        r"<style>.*?</style>",
        f"<style>{font_style_block('*')}</style>",
        svg,
        count=1,
        flags=re.S,
    )

    svg = re.sub(
        r'(<text x="30" y="40" style=")[^"]*(">)',
        rf'\1font-size: 22px; font-weight: 600; fill: {title_color};\2',
        svg,
        count=1,
    )

    svg = re.sub(
        r'font-family="[^"]+"',
        f'font-family="{EMBEDDED_FONT_FAMILY}"',
        svg,
    )

    return svg


def main():
    for theme in THEMES:
        outdir = Path("profile-summary-card-output") / theme
        outdir.mkdir(parents=True, exist_ok=True)

        for card, filename in CARDS:
            url = f"{BASE}/{card}?username={USER}&theme={theme}"
            path = outdir / filename

            try:
                data = fetch(url)
            except RuntimeError as error:
                if path.exists():
                    print(f"warning: keeping existing {path}: {error}")
                    continue
                raise

            if b"<svg" not in data[:500]:
                if path.exists():
                    print(f"warning: keeping existing {path}: unexpected response for {url}")
                    continue
                raise RuntimeError(f"Unexpected response for {url}")

            svg = normalize_svg(data.decode("utf-8"), theme)
            path.write_text(svg, encoding="utf-8")
            print(f"wrote {path}")


if __name__ == "__main__":
    main()
