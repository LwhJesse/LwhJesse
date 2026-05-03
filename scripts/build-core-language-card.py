#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

OWNER = os.environ.get("GITHUB_REPOSITORY_OWNER", "LwhJesse")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

MAX_NAMED_LANGS = 5   # 前5种单独显示
MAX_DISPLAY_ITEMS = 6 # 最终最多6项：前5 + Other
PINNED_LANGS = {"CUDA"}

CARD_W = 495
CARD_H = 235
CARD_RX = 12
CARD_RY = 12

OUT_LIGHT = Path("assets/core-repo-languages-light.svg")
OUT_DARK = Path("assets/core-repo-languages-dark.svg")

LANG_COLORS = {
    "Python": "#3572A5",
    "CUDA": "#76B900",
    "C++": "#f34b7d",
    "JavaScript": "#f1e05a",
    "Shell": "#89e051",
    "Lua": "#000080",
    "CMake": "#DA3434",
    "C": "#555555",
    "Java": "#b07219",
    "Go": "#00ADD8",
    "C#": "#178600",
    "Assembly": "#6E4C13",
    "Other": "#8b949e",
}

THEMES = {
    "light": {
        "bg": "#ffffff",
        "border": "#d0d7de",
        "title": "#0969da",
        "text": "#57606a",
        "strong": "#24292f",
        "muted": "#6e7781",
        "bar_bg": "#eaeef2",
    },
    "dark": {
        "bg": "#0d1117",
        "border": "#30363d",
        "title": "#2f81f7",
        "text": "#8b949e",
        "strong": "#c9d1d9",
        "muted": "#8b949e",
        "bar_bg": "#21262d",
    },
}

def gh_get(url: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-card-builder",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)

def normalize_lang_name(name: str) -> str:
    n = name.strip()
    low = n.lower()
    if low == "cuda":
        return "CUDA"
    return n

def list_owned_public_nonfork_repos(owner: str):
    url = f"https://api.github.com/users/{owner}/repos?per_page=100&type=owner&sort=updated"
    repos = gh_get(url)
    out = []
    for repo in repos:
        if repo.get("private"):
            continue
        if repo.get("fork"):
            continue
        if repo.get("archived"):
            continue
        if repo.get("name", "").lower() == owner.lower():
            continue
        out.append(repo)
    return out

def collect_language_totals(owner: str):
    repos = list_owned_public_nonfork_repos(owner)
    total = {}
    counted_repos = []

    for repo in repos:
        data = gh_get(repo["languages_url"])
        if not isinstance(data, dict):
            continue
        repo_total = 0
        for lang, value in data.items():
            if not value:
                continue
            key = normalize_lang_name(lang)
            total[key] = total.get(key, 0) + int(value)
            repo_total += int(value)
        if repo_total > 0:
            counted_repos.append(repo["name"])

    return total, counted_repos

def select_display_languages(total):
    merged = {}
    for lang, value in total.items():
        if value > 0:
            merged[lang] = merged.get(lang, 0) + value

    total_bytes = sum(merged.values())
    if total_bytes <= 0:
        return [("Other", 0)], 0

    ordered = sorted(merged.items(), key=lambda kv: kv[1], reverse=True)

    top = ordered[:MAX_NAMED_LANGS]

    if "CUDA" in merged and not any(lang == "CUDA" for lang, _ in top):
        if top:
            smallest_idx = min(range(len(top)), key=lambda i: top[i][1])
            top[smallest_idx] = ("CUDA", merged["CUDA"])
            dedup = {}
            for lang, val in top:
                dedup[lang] = val
            top = sorted(dedup.items(), key=lambda kv: kv[1], reverse=True)[:MAX_NAMED_LANGS]

    selected_names = {lang for lang, _ in top}
    other_value = sum(val for lang, val in merged.items() if lang not in selected_names)

    result = list(top)
    if other_value > 0:
        result.append(("Other", other_value))

    result = result[:MAX_DISPLAY_ITEMS]
    return result, total_bytes

def color_for_lang(lang: str) -> str:
    return LANG_COLORS.get(lang, "#8b949e")

def fmt_pct(value: int, total_bytes: int) -> str:
    if total_bytes <= 0:
        return "0.0%"
    return f"{value * 100.0 / total_bytes:.1f}%"

def render_svg(theme_name: str, langs, total_bytes: int, repo_count: int) -> str:
    th = THEMES[theme_name]

    bar_x = 34
    bar_y = 78
    bar_w = 427
    bar_h = 12
    bar_rx = 6

    legend_x0 = 44
    legend_y0 = 120
    legend_col_w = 135
    legend_row_h = 38

    clip_id = f"barclip-{theme_name}"

    segs = []
    cursor = bar_x
    for i, (lang, value) in enumerate(langs):
        pct = 0 if total_bytes == 0 else value / total_bytes
        w = bar_w * pct
        if i == len(langs) - 1:
            w = (bar_x + bar_w) - cursor
        segs.append(
            f'<rect x="{cursor:.3f}" y="{bar_y}" width="{w:.3f}" height="{bar_h}" fill="{color_for_lang(lang)}" />'
        )
        cursor += w

    legend_items = []
    for i, (lang, value) in enumerate(langs):
        col = i % 3
        row = i // 3
        x = legend_x0 + col * legend_col_w
        y = legend_y0 + row * legend_row_h
        pct_text = fmt_pct(value, total_bytes)

        legend_items.append(
            f'''
            <g transform="translate({x},{y})">
              <circle cx="0" cy="0" r="6.5" fill="{color_for_lang(lang)}" />
              <text x="16" y="4" font-size="11" font-weight="600" fill="{th["strong"]}">{escape(lang)}</text>
              <text x="70" y="4" font-size="11" fill="{th["text"]}">{pct_text}</text>
            </g>
            '''
        )

    repos_line = (
        f"Repos counted: {repo_count} · Forks, archived repositories, and the profile repository are excluded."
    )

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{CARD_W}" height="{CARD_H}" viewBox="0 0 {CARD_W} {CARD_H}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" width="{CARD_W-1}" height="{CARD_H-1}" rx="{CARD_RX}" ry="{CARD_RY}"
        fill="{th["bg"]}" stroke="{th["border"]}"/>

  <text x="24" y="34" font-size="18" font-weight="600" fill="{th["title"]}">Core Repository Languages</text>
  <text x="24" y="54" font-size="10.5" fill="{th["muted"]}">Owned public non-fork repositories · GitHub language bytes</text>

  <defs>
    <clipPath id="{clip_id}">
      <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="{bar_rx}" ry="{bar_rx}" />
    </clipPath>
  </defs>

  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="{bar_rx}" ry="{bar_rx}" fill="{th["bar_bg"]}" />
  <g clip-path="url(#{clip_id})">
    {''.join(segs)}
  </g>

  {''.join(legend_items)}

  <text x="24" y="214" font-size="10" fill="{th["muted"]}">{escape(repos_line)}</text>
</svg>
'''
    return svg

def main():
    total, counted_repos = collect_language_totals(OWNER)
    langs, total_bytes = select_display_languages(total)

    OUT_LIGHT.write_text(render_svg("light", langs, total_bytes, len(counted_repos)), encoding="utf-8")
    OUT_DARK.write_text(render_svg("dark", langs, total_bytes, len(counted_repos)), encoding="utf-8")

    print("Generated core repository language cards:")
    for lang, value in langs:
        print(f"{lang:<14} {fmt_pct(value, total_bytes):>6}")

if __name__ == "__main__":
    main()
