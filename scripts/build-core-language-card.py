#!/usr/bin/env python3
import json
import os
import urllib.request
from pathlib import Path

USER = os.environ.get("GITHUB_REPOSITORY_OWNER", "LwhJesse")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

EXCLUDE_REPOS = {USER}
MAX_LANGS = 5

DISPLAY_NAME = {
    "Cuda": "CUDA",
}

COLORS = {
    "Python": "#3572A5",
    "Cuda": "#76B900",
    "C++": "#f34b7d",
    "JavaScript": "#f1e05a",
    "Shell": "#89e051",
    "CMake": "#DA3434",
    "C": "#555555",
    "Lua": "#000080",
    "Dart": "#00B4AB",
    "TypeScript": "#3178c6",
    "Other": "#8b949e",
}

THEMES = {
    "light": {
        "bg": "#ffffff",
        "border": "#d0d7de",
        "track": "#f6f8fa",
        "title": "#0969da",
        "text": "#24292f",
        "muted": "#57606a",
    },
    "dark": {
        "bg": "#0d1117",
        "border": "#30363d",
        "track": "#161b22",
        "title": "#58a6ff",
        "text": "#c9d1d9",
        "muted": "#8b949e",
    },
}


def get_json(url: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "LwhJesse-core-language-card",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def fetch_owned_nonfork_repos():
    repos = []
    page = 1

    while True:
        url = f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}&sort=updated"
        data = get_json(url)
        if not data:
            break
        repos.extend(data)
        page += 1

    result = []
    for repo in repos:
        if repo.get("fork"):
            continue
        if repo.get("archived"):
            continue
        if repo["name"] in EXCLUDE_REPOS:
            continue
        result.append(repo)

    return result


def collect_languages(repos):
    total = {}
    for repo in repos:
        langs = get_json(repo["languages_url"])
        for lang, n in langs.items():
            total[lang] = total.get(lang, 0) + int(n)
    return total


def display_languages(total):
    if not total:
        return [("Other", 1)], 1

    total_bytes = sum(total.values())
    items = sorted(total.items(), key=lambda x: x[1], reverse=True)

    keep = []
    used = set()

    if "Cuda" in total:
        keep.append(("Cuda", total["Cuda"]))
        used.add("Cuda")

    for lang, n in items:
        if lang in used:
            continue
        if len(keep) >= MAX_LANGS:
            break
        keep.append((lang, n))
        used.add(lang)

    other = sum(n for lang, n in items if lang not in used)
    if other > 0:
        keep.append(("Other", other))

    keep = sorted(keep, key=lambda x: x[1], reverse=True)
    return keep, total_bytes


def esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def make_svg(total, repo_count, theme_name):
    t = THEMES[theme_name]
    langs, total_bytes = display_languages(total)

    width = 510
    height = 250

    bar_x = 30
    bar_y = 86
    bar_w = 450
    bar_h = 12

    clip_id = f"core-lang-bar-{theme_name}"

    out = []
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    out.append("  <defs>")
    out.append(f'    <clipPath id="{clip_id}">')
    out.append(f'      <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="6" ry="6"/>')
    out.append("    </clipPath>")
    out.append("  </defs>")

    out.append(f'  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" fill="{t["bg"]}" stroke="{t["border"]}"/>')

    out.append(f'  <text x="30" y="34" font-family="Georgia, Times New Roman, serif" font-size="21" fill="{t["title"]}">Core Repository Languages</text>')
    out.append(f'  <text x="30" y="52" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="10" fill="{t["muted"]}">owned public non-fork repositories · GitHub language bytes</text>')

    out.append(f'  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="6" fill="{t["track"]}" stroke="{t["border"]}"/>')
    out.append(f'  <g clip-path="url(#{clip_id})">')

    cursor = bar_x
    for lang, n in langs:
        seg_w = bar_w * (n / total_bytes)
        color = COLORS.get(lang, "#8b949e")
        out.append(f'    <rect x="{cursor:.2f}" y="{bar_y}" width="{seg_w:.2f}" height="{bar_h}" fill="{color}"/>')
        cursor += seg_w

    out.append("  </g>")

    # 两列三行，和左边 donut 卡的视觉高度更接近
    col_x = [34, 255]
    row_y = [132, 165, 198]

    for i, (lang, n) in enumerate(langs[:6]):
        col = i % 2
        row = i // 2
        lx = col_x[col]
        ly = row_y[row]

        pct = 100 * n / total_bytes
        name = DISPLAY_NAME.get(lang, lang)
        color = COLORS.get(lang, "#8b949e")

        out.append(f'  <circle cx="{lx + 6}" cy="{ly - 5}" r="5.5" fill="{color}"/>')
        out.append(f'  <text x="{lx + 20}" y="{ly}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="13" font-weight="600" fill="{t["text"]}">{esc(name)}</text>')
        out.append(f'  <text x="{lx + 118}" y="{ly}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="12" fill="{t["muted"]}">{pct:.1f}%</text>')

    out.append(f'  <text x="30" y="234" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="9.5" fill="{t["muted"]}">Repos counted: {repo_count} · Forks, archived repositories, and the profile repository are excluded.</text>')

    out.append("</svg>")
    return "\n".join(out)


def main():
    repos = fetch_owned_nonfork_repos()
    total = collect_languages(repos)

    Path("assets").mkdir(exist_ok=True)

    Path("assets/core-repo-languages-light.svg").write_text(
        make_svg(total, len(repos), "light")
    )
    Path("assets/core-repo-languages-dark.svg").write_text(
        make_svg(total, len(repos), "dark")
    )

    langs, total_bytes = display_languages(total)
    print("Generated core repository language cards:")
    for lang, n in langs:
        print(f"{DISPLAY_NAME.get(lang, lang):16s} {100 * n / total_bytes:5.1f}%")


if __name__ == "__main__":
    main()
