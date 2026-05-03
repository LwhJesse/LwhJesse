#!/usr/bin/env python3
import json
import os
import urllib.request
from pathlib import Path

USER = os.environ.get("GITHUB_REPOSITORY_OWNER", "LwhJesse")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

EXCLUDE_REPOS = {
    USER,  # profile README repo
}

DISPLAY_NAME = {
    "Cuda": "CUDA",
    "C++": "C++",
    "Python": "Python",
    "JavaScript": "JavaScript",
    "Shell": "Shell",
    "CMake": "CMake",
    "Other": "Other",
}

COLORS = {
    "Cuda": "#76B900",
    "C++": "#f34b7d",
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "Shell": "#89e051",
    "CMake": "#DA3434",
    "Other": "#8b949e",
}

def get_json(url: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "LwhJesse-core-language-card",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as r:
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

    out = []
    for repo in repos:
        if repo.get("fork"):
            continue
        if repo.get("archived"):
            continue
        if repo["name"] in EXCLUDE_REPOS:
            continue
        out.append(repo)
    return out

def collect_languages(repos):
    total = {}
    counted_repos = []

    for repo in repos:
        langs = get_json(repo["languages_url"])
        if not langs:
            continue

        counted_repos.append(repo["name"])
        for lang, n in langs.items():
            total[lang] = total.get(lang, 0) + int(n)

    return total, counted_repos

def escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
    )

def prepare_display_languages(total):
    total_bytes = sum(total.values()) or 1

    # 先按字节数降序
    items = sorted(total.items(), key=lambda x: x[1], reverse=True)

    # 小于 3% 的语言并入 Other
    major = []
    other_sum = 0
    for lang, n in items:
        pct = n / total_bytes
        if pct < 0.03:
            other_sum += n
        else:
            major.append((lang, n))

    if other_sum > 0:
        major.append(("Other", other_sum))

    # 最多显示 5 项；如果超过 5 项，把后面的再并入 Other
    if len(major) > 5:
        kept = major[:4]
        merged_other = sum(n for _, n in major[4:])
        has_other = any(lang == "Other" for lang, _ in kept)
        if has_other:
            new_kept = []
            for lang, n in kept:
                if lang == "Other":
                    new_kept.append((lang, n + merged_other))
                else:
                    new_kept.append((lang, n))
            major = new_kept
        else:
            major = kept + [("Other", merged_other)]

    return major, total_bytes

def make_svg(total, repos, theme):
    dark = theme == "dark"

    bg = "#0d1117" if dark else "#ffffff"
    border = "#30363d" if dark else "#d0d7de"
    title = "#58a6ff" if dark else "#0969da"
    text = "#c9d1d9" if dark else "#24292f"
    muted = "#8b949e" if dark else "#57606a"
    track = "#161b22" if dark else "#f6f8fa"

    langs, total_bytes = prepare_display_languages(total)

    width = 700
    height = 270
    pad_x = 30

    bar_x = pad_x
    bar_y = 84
    bar_w = width - 2 * pad_x
    bar_h = 16
    radius = 8

    parts = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    parts.append("  <defs>")
    parts.append(f'    <clipPath id="bar-clip-{theme}">')
    parts.append(f'      <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="{radius}" ry="{radius}" />')
    parts.append("    </clipPath>")
    parts.append("  </defs>")

    parts.append(f'  <rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="12" fill="{bg}" stroke="{border}" />')
    parts.append(f'  <text x="{pad_x}" y="38" font-family="Georgia, Times New Roman, serif" font-size="25" fill="{title}">Core Repository Languages</text>')
    parts.append(f'  <text x="{pad_x}" y="60" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="12" fill="{muted}">Owned public non-fork repositories · GitHub language bytes</text>')

    # 先画轨道
    parts.append(f'  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="{radius}" ry="{radius}" fill="{track}" stroke="{border}" />')

    # 再用 clipPath 裁剪 stacked bar，保证两端天然圆角完整
    parts.append(f'  <g clip-path="url(#bar-clip-{theme})">')
    cursor = bar_x
    for lang, n in langs:
        frac = n / total_bytes
        seg_w = bar_w * frac
        color = COLORS.get(lang, "#8b949e")
        parts.append(f'    <rect x="{cursor:.2f}" y="{bar_y}" width="{seg_w:.2f}" height="{bar_h}" fill="{color}" />')
        cursor += seg_w
    parts.append("  </g>")

    # 图例：最多 5 项，2 行排布
    legend = []
    for lang, n in langs:
        pct = 100 * n / total_bytes
        legend.append((DISPLAY_NAME.get(lang, lang), pct, COLORS.get(lang, "#8b949e")))

    col_x = [pad_x, pad_x + 235, pad_x + 470]
    row_y0 = 140

    for i, (name, pct, color) in enumerate(legend):
        col = i % 3
        row = i // 3
        lx = col_x[col]
        ly = row_y0 + row * 42

        parts.append(f'  <circle cx="{lx+7}" cy="{ly-5}" r="6" fill="{color}" />')
        parts.append(f'  <text x="{lx+24}" y="{ly}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="16" font-weight="600" fill="{text}">{escape(name)}</text>')
        parts.append(f'  <text x="{lx+145}" y="{ly}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="15" fill="{muted}">{pct:.1f}%</text>')

    parts.append(f'  <text x="{pad_x}" y="{height-20}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="11" fill="{muted}">Repos counted: {len(repos)} · Forks and the profile repository are excluded.</text>')
    parts.append("</svg>")
    return "\n".join(parts)

def main():
    repos = fetch_owned_nonfork_repos()
    total, counted_repos = collect_languages(repos)

    Path("assets").mkdir(exist_ok=True)

    Path("assets/core-repo-languages-light.svg").write_text(
        make_svg(total, counted_repos, "light")
    )
    Path("assets/core-repo-languages-dark.svg").write_text(
        make_svg(total, counted_repos, "dark")
    )

    langs, total_bytes = prepare_display_languages(total)

    print("Displayed language totals:")
    for lang, n in langs:
        pct = 100 * n / total_bytes
        print(f"{DISPLAY_NAME.get(lang, lang):16s} {n:8d}  {pct:5.1f}%")

    print()
    print("Repos counted:")
    for repo in counted_repos:
        print(f"- {repo}")

if __name__ == "__main__":
    main()
