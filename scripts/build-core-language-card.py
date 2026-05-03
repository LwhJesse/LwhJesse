#!/usr/bin/env python3
import hashlib
import json
import os
import urllib.request
from pathlib import Path

USER = os.environ.get("GITHUB_REPOSITORY_OWNER", "LwhJesse")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

# 排除 profile README 仓库本身
EXCLUDE_REPOS = {USER}

# 最多显示 5 个具名语言；其余全部合并到 Other
MAX_NAMED_LANGS = 5

# 这些语言只要存在，就强制保留
PINNED_LANGS = {"Cuda"}

DISPLAY_NAME = {
    "Cuda": "CUDA",
}

COLORS = {
    "Python": "#3572A5",
    "Cuda": "#76B900",
    "C++": "#f34b7d",
    "C": "#555555",
    "C#": "#178600",
    "Java": "#b07219",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Assembly": "#6E4C13",
    "CMake": "#DA3434",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Shell": "#89e051",
    "Lua": "#000080",
    "Dart": "#00B4AB",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Makefile": "#427819",
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


def fallback_color(name: str) -> str:
    h = hashlib.sha1(name.encode("utf-8")).hexdigest()
    return f"#{h[:6]}"


def color_for(lang: str) -> str:
    return COLORS.get(lang, fallback_color(lang))


def display_name(lang: str) -> str:
    return DISPLAY_NAME.get(lang, lang)


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


def select_display_languages(total):
    """
    规则：
    1. CUDA 只要存在就强制保留
    2. 其余语言按字节数从大到小取
    3. 最多显示 5 个具名语言
    4. 其余全部合并为 Other
    5. 最终图例最多 6 项（5 个具名 + Other）
    """
    if not total:
        return [("Other", 1)], 1

    total_bytes = sum(total.values())
    ranked = sorted(total.items(), key=lambda x: x[1], reverse=True)

    selected = []
    selected_names = set()

    # 先保留 pinned 语言（比如 CUDA）
    for lang in PINNED_LANGS:
        if lang in total and lang not in selected_names:
            selected.append((lang, total[lang]))
            selected_names.add(lang)

    # 再从大到小补齐到 MAX_NAMED_LANGS
    for lang, n in ranked:
        if lang in selected_names:
            continue
        if len(selected) >= MAX_NAMED_LANGS:
            break
        selected.append((lang, n))
        selected_names.add(lang)

    other = sum(n for lang, n in ranked if lang not in selected_names)
    if other > 0:
        selected.append(("Other", other))

    # 最后按大小重新排序，让条形图和图例更自然
    selected = sorted(selected, key=lambda x: x[1], reverse=True)
    return selected, total_bytes


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
    langs, total_bytes = select_display_languages(total)

    # 固定尺寸；README 里统一 width=62% 缩放
    width = 820
    height = 220

    bar_x = 36
    bar_y = 74
    bar_w = 748
    bar_h = 14

    clip_id = f"core-lang-bar-{theme_name}"

    out = []
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    )
    out.append("  <defs>")
    out.append(f'    <clipPath id="{clip_id}">')
    out.append(
        f'      <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="7" ry="7"/>'
    )
    out.append("    </clipPath>")
    out.append("  </defs>")

    out.append(
        f'  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="14" fill="{t["bg"]}" stroke="{t["border"]}"/>'
    )

    out.append(
        f'  <text x="36" y="34" font-family="Georgia, Times New Roman, serif" font-size="24" fill="{t["title"]}">Core Repository Languages</text>'
    )
    out.append(
        f'  <text x="36" y="54" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="11" fill="{t["muted"]}">owned public non-fork repositories · GitHub language bytes</text>'
    )

    out.append(
        f'  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="7" fill="{t["track"]}" stroke="{t["border"]}"/>'
    )
    out.append(f'  <g clip-path="url(#{clip_id})">')

    cursor = bar_x
    for lang, n in langs:
        seg_w = bar_w * (n / total_bytes)
        out.append(
            f'    <rect x="{cursor:.2f}" y="{bar_y}" width="{seg_w:.2f}" height="{bar_h}" fill="{color_for(lang)}"/>'
        )
        cursor += seg_w

    out.append("  </g>")

    # 固定两行三列。无论语言怎么杂，都最多显示 6 项。
    col_x = [48, 300, 548]
    row_y = [128, 168]

    for i, (lang, n) in enumerate(langs[:6]):
        col = i % 3
        row = i // 3
        lx = col_x[col]
        ly = row_y[row]

        pct = 100 * n / total_bytes
        name = display_name(lang)

        out.append(f'  <circle cx="{lx + 7}" cy="{ly - 6}" r="6.5" fill="{color_for(lang)}"/>')
        out.append(
            f'  <text x="{lx + 24}" y="{ly}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="15" font-weight="600" fill="{t["text"]}">{esc(name)}</text>'
        )
        out.append(
            f'  <text x="{lx + 126}" y="{ly}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="14" fill="{t["muted"]}">{pct:.1f}%</text>'
        )

    out.append(
        f'  <text x="36" y="204" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="10" fill="{t["muted"]}">Repos counted: {repo_count} · Forks, archived repositories, and the profile repository are excluded.</text>'
    )

    out.append("</svg>")
    return "\n".join(out)


def main():
    repos = fetch_owned_nonfork_repos()
    total = collect_languages(repos)

    Path("assets").mkdir(exist_ok=True)

    Path("assets/core-repo-languages-light.svg").write_text(
        make_svg(total, len(repos), "light"),
        encoding="utf-8",
    )
    Path("assets/core-repo-languages-dark.svg").write_text(
        make_svg(total, len(repos), "dark"),
        encoding="utf-8",
    )

    langs, total_bytes = select_display_languages(total)
    print("Generated core repository language cards:")
    for lang, n in langs:
        print(f"{display_name(lang):16s} {100 * n / total_bytes:5.1f}%")


if __name__ == "__main__":
    main()
