#!/usr/bin/env python3
import os
import urllib.request
from pathlib import Path

USER = os.environ.get("GITHUB_REPOSITORY_OWNER", "LwhJesse")

CARDS = [
    ("profile-details", "0-profile-details.svg"),
    ("most-commit-language", "2-most-commit-language.svg"),
    ("stats", "3-stats.svg"),
]

THEMES = ["github", "github_dark"]

BASE = "https://github-profile-summary-cards.vercel.app/api/cards"

def fetch(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "LwhJesse-profile-card-fetcher"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

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
            path.write_bytes(data)
            print(f"wrote {path}")

if __name__ == "__main__":
    main()
