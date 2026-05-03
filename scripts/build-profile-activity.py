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
        "title": "#24292f",
        "accent": "#0969da",
        "text": "#24292f",
        "muted": "#57606a",
        "chip_bg": "#f6f8fa",
    },
    "dark": {
        "bg": "#0d1117",
        "border": "#30363d",
        "track": "#161b22",
        "title": "#e6edf3",
        "accent": "#58a6ff",
        "text": "#c9d1d9",
        "muted": "#8b949e",
        "chip_bg": "#161b22",
    },
}

def get_json(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "LwhJesse-profile-activity",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def fetch_user():
    return get_json(f"https://api.github.com/users/{USER}")

def fetch_repos():
    repos = []
    page = 1

    while True:
        url = f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}&sort=updated"
        data = get_json(url)
        if not data:
            break
        repos.extend(data)
        page += 1

    owned = []
    for repo in repos:
        if repo.get("fork"):
            continue
        if repo.get("archived"):
            continue
        if repo["name"] in EXCLUDE_REPOS:
            continue
        owned.append(repo)

    return owned

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
    sorted_items = sorted(total.items(), key=lambda x: x[1], reverse=True)

    keep = []
    used = set()

    if "Cuda" in total:
        keep.append(("Cuda", total["Cuda"]))
        used.add("Cuda")

    for lang, n in sorted_items:
        if lang in used:
            continue
        if len(keep) >= MAX_LANGS:
            break
        keep.append((lang, n))
        used.add(lang)

    other = sum(n for lang, n in sorted_items if lang not in used)
    if other > 0:
        keep.append(("Other", other))

    keep = sorted(keep, key=lambda x: x[1], reverse=True)
    return keep, total_bytes

def esc(s):
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

def render_svg(theme_name, user, repos, langs_total):
    t = THEMES[theme_name]
    langs, total_bytes = display_languages(langs_total)

    stars = sum(int(r.get("stargazers_count", 0)) for r in repos)
    forks = sum(int(r.get("forks_count", 0)) for r in repos)
    public_repos = int(user.get("public_repos", 0))
    counted_repos = len(repos)

    width = 960
    height = 230

    bar_x = 42
    bar_y = 122
    bar_w = 876
    bar_h = 14

    clip_id = f"lang-bar-{theme_name}"

    out = []
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    out.append("  <defs>")
    out.append(f'    <clipPath id="{clip_id}">')
    out.append(f'      <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="7" ry="7"/>')
    out.append("    </clipPath>")
    out.append("  </defs>")

    out.append(f'  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="18" fill="{t["bg"]}" stroke="{t["border"]}" />')

    out.append(f'  <text x="42" y="42" font-family="Georgia, Times New Roman, serif" font-size="25" fill="{t["accent"]}">GitHub Activity</text>')
    out.append(f'  <text x="42" y="66" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="12" fill="{t["muted"]}">compact public profile signals · generated automatically</text>')

    chips = [
        f"{public_repos} public repos",
        f"{counted_repos} core repos",
        f"{stars} stars",
        f"{forks} forks",
    ]

    x = 42
    for label in chips:
        chip_w = max(92, 18 + len(label) * 8)
        out.append(f'  <rect x="{x}" y="78" width="{chip_w}" height="28" rx="14" fill="{t["chip_bg"]}" stroke="{t["border"]}" />')
        out.append(f'  <text x="{x + 15}" y="97" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="13" fill="{t["text"]}">{esc(label)}</text>')
        x += chip_w + 12

    out.append(f'  <text x="42" y="115" font-family="Georgia, Times New Roman, serif" font-size="20" fill="{t["title"]}">Core Repository Languages</text>')

    out.append(f'  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="7" fill="{t["track"]}" stroke="{t["border"]}" />')
    out.append(f'  <g clip-path="url(#{clip_id})">')

    cursor = bar_x
    for lang, n in langs:
        seg_w = bar_w * (n / total_bytes)
        color = COLORS.get(lang, "#8b949e")
        out.append(f'    <rect x="{cursor:.2f}" y="{bar_y}" width="{seg_w:.2f}" height="{bar_h}" fill="{color}" />')
        cursor += seg_w

    out.append("  </g>")

    col_x = [42, 220, 398, 576, 754]
    row_y = [170, 200]

    for i, (lang, n) in enumerate(langs[:10]):
        col = i % 5
        row = i // 5
        lx = col_x[col]
        ly = row_y[row]
        pct = 100 * n / total_bytes
        name = DISPLAY_NAME.get(lang, lang)
        color = COLORS.get(lang, "#8b949e")

        out.append(f'  <circle cx="{lx + 6}" cy="{ly - 5}" r="6" fill="{color}" />')
        out.append(f'  <text x="{lx + 20}" y="{ly}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="14" font-weight="600" fill="{t["text"]}">{esc(name)}</text>')
        out.append(f'  <text x="{lx + 102}" y="{ly}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="13" fill="{t["muted"]}">{pct:.1f}%</text>')

    out.append(f'  <text x="42" y="218" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="10" fill="{t["muted"]}">Forks, archived repositories, and the profile README repository are excluded from language calculation.</text>')

    out.append("</svg>")
    return "\n".join(out)

def main():
    user = fetch_user()
    repos = fetch_repos()
    langs_total = collect_languages(repos)

    Path("assets").mkdir(exist_ok=True)

    Path("assets/profile-activity-light.svg").write_text(
        render_svg("light", user, repos, langs_total)
    )
    Path("assets/profile-activity-dark.svg").write_text(
        render_svg("dark", user, repos, langs_total)
    )

    langs, total_bytes = display_languages(langs_total)
    print("Generated profile activity card:")
    for lang, n in langs:
        print(f"{DISPLAY_NAME.get(lang, lang):16s} {100 * n / total_bytes:5.1f}%")

if __name__ == "__main__":
    main()
