from __future__ import annotations

import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

USER = "LwhJesse"
API = "https://api.github.com"
TOKEN = (
    os.environ.get("GITHUB_TOKEN")
    or os.environ.get("GH_TOKEN")
    or os.environ.get("SUMMARY_GITHUB_TOKEN")
)

OUT_DIR = Path("assets")
OUT_DIR.mkdir(parents=True, exist_ok=True)

LANG_COLORS = {
    "C++": "#f34b7d",
    "C": "#555555",
    "C/C++": "#f34b7d",
    "CUDA": "#76b900",
    "Python": "#3572A5",
    "GLSL": "#5686a5",
    "Markdown": "#083fa1",
    "reStructuredText": "#141414",
    "YAML": "#cb171e",
    "JSON": "#292929",
    "Shell": "#89e051",
    "Lua": "#000080",
    "CMake": "#DA3434",
    "TOML": "#9c4221",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Dart": "#00B4AB",
    "Other": "#6e7681",
}

EXTENSION_LANGUAGE = {
    ".cu": "CUDA",
    ".cuh": "CUDA",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".hh": "C++",
    ".hxx": "C++",
    ".c": "C",
    ".h": "C/C++",
    ".glsl": "GLSL",
    ".frag": "GLSL",
    ".vert": "GLSL",
    ".comp": "GLSL",
    ".py": "Python",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".lua": "Lua",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".html": "HTML",
    ".css": "CSS",
    ".dart": "Dart",
    ".cmake": "CMake",
}

SPECIAL_FILENAMES = {
    "CMakeLists.txt": "CMake",
    "Makefile": "Makefile",
    "Dockerfile": "Dockerfile",
}


def request_json(url: str) -> tuple[Any, dict[str, str]]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "LwhJesse-profile-language-cards",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body), dict(resp.headers)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API failed: {e.code} {url}\n{detail}") from e


def build_url(path: str, params: dict[str, Any] | None = None) -> str:
    if path.startswith("https://"):
        return path

    query = urllib.parse.urlencode(params or {})
    return f"{API}{path}" + (f"?{query}" if query else "")


def next_link(headers: dict[str, str]) -> str | None:
    link = headers.get("Link") or headers.get("link")
    if not link:
        return None

    for part in link.split(","):
        section = part.strip()
        if 'rel="next"' in section:
            match = re.match(r"<([^>]+)>", section)
            if match:
                return match.group(1)

    return None


def paged_items(path: str, params: dict[str, Any] | None, key: str | None = None) -> list[Any]:
    url = build_url(path, params)
    out: list[Any] = []

    while url:
        data, headers = request_json(url)

        if key is None:
            if not isinstance(data, list):
                raise RuntimeError(f"Expected list response from {url}")
            out.extend(data)
        else:
            out.extend(data.get(key, []))

        url = next_link(headers)
        time.sleep(0.15)

    return out


def language_from_filename(filename: str) -> str:
    base = Path(filename).name
    if base in SPECIAL_FILENAMES:
        return SPECIAL_FILENAMES[base]

    suffix = Path(filename).suffix
    if suffix in EXTENSION_LANGUAGE:
        return EXTENSION_LANGUAGE[suffix]

    if filename.endswith(".cu.in") or filename.endswith(".cuh.in"):
        return "CUDA"

    if filename.endswith(".cpp.in") or filename.endswith(".hpp.in"):
        return "C++"

    return "Other"


def parse_pr_ref(item: dict[str, Any]) -> tuple[str, str, int] | None:
    html_url = item.get("html_url", "")
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)$", html_url)

    if not match:
        return None

    owner = match.group(1)
    repo = match.group(2)
    number = int(match.group(3))

    return owner, repo, number


def external_contribution_languages() -> Counter[str]:
    stats: Counter[str] = Counter()

    prs = paged_items(
        "/search/issues",
        {
            "q": f"is:pr author:{USER} archived:false",
            "per_page": 100,
        },
        key="items",
    )

    seen: set[tuple[str, str, int]] = set()

    for item in prs:
        parsed = parse_pr_ref(item)
        if parsed is None:
            continue

        owner, repo, number = parsed
        pr_key = (owner.lower(), repo.lower(), number)

        if pr_key in seen:
            continue
        seen.add(pr_key)

        if owner.lower() == USER.lower():
            continue

        files = paged_items(
            f"/repos/{owner}/{repo}/pulls/{number}/files",
            {"per_page": 100},
            key=None,
        )

        for changed_file in files:
            filename = str(changed_file.get("filename", ""))
            language = language_from_filename(filename)

            changes = int(changed_file.get("changes") or 0)
            if changes <= 0:
                changes = int(changed_file.get("additions") or 0) + int(changed_file.get("deletions") or 0)
            if changes <= 0:
                changes = 1

            stats[language] += changes

    return stats


def own_repository_languages() -> Counter[str]:
    stats: Counter[str] = Counter()

    repos = paged_items(
        f"/users/{USER}/repos",
        {
            "per_page": 100,
            "type": "owner",
            "sort": "updated",
        },
        key=None,
    )

    for repo in repos:
        owner = repo.get("owner", {}).get("login", "")
        name = repo.get("name", "")

        if owner.lower() != USER.lower():
            continue

        if name == USER:
            continue

        if repo.get("fork"):
            continue

        if repo.get("archived"):
            continue

        languages_url = repo.get("languages_url")
        if not languages_url:
            continue

        languages, _ = request_json(languages_url)

        for language, byte_count in languages.items():
            stats[str(language)] += int(byte_count)

    return stats



def get_profile_title_style(dark: bool) -> str:
    svg_path = Path("profile-summary-card-output/github_dark/0-profile-details.svg" if dark else "profile-summary-card-output/github/0-profile-details.svg")
    root = ET.fromstring(svg_path.read_text(encoding="utf-8"))
    for elem in root.iter():
        if elem.tag.endswith("text") and (elem.text or "").strip() == USER:
            style = elem.attrib.get("style", "").strip()
            if style:
                return style
    raise RuntimeError(f"Could not find title style for {USER} in {svg_path}")

def xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def top_items(stats: Counter[str], limit: int = 6) -> list[tuple[str, int]]:
    positive_items = [(language, value) for language, value in stats.most_common() if value > 0]

    other_slot = limit - 1

    if len(positive_items) <= other_slot:
        return positive_items

    head = positive_items[:other_slot]
    other_total = sum(value for _, value in positive_items[other_slot:])

    if other_total > 0:
        head.append(("Other", other_total))

    return head

def donut_arc_path(cx: float, cy: float, r_outer: float, r_inner: float, start: float, end: float) -> str:
    if end - start >= math.tau:
        end = start + math.tau - 0.0001

    large_arc = 1 if end - start > math.pi else 0

    x1 = cx + r_outer * math.cos(start)
    y1 = cy + r_outer * math.sin(start)
    x2 = cx + r_outer * math.cos(end)
    y2 = cy + r_outer * math.sin(end)

    x3 = cx + r_inner * math.cos(end)
    y3 = cy + r_inner * math.sin(end)
    x4 = cx + r_inner * math.cos(start)
    y4 = cy + r_inner * math.sin(start)

    return (
        f"M{x1:.3f},{y1:.3f} "
        f"A{r_outer:.3f},{r_outer:.3f},0,{large_arc},1,{x2:.3f},{y2:.3f} "
        f"L{x3:.3f},{y3:.3f} "
        f"A{r_inner:.3f},{r_inner:.3f},0,{large_arc},0,{x4:.3f},{y4:.3f} "
        "Z"
    )


def write_svg(path: Path, title: str, stats: Counter[str], dark: bool) -> None:
    items = top_items(stats, limit=6)
    total = sum(value for _, value in items)

    bg = "#0d1117" if dark else "#ffffff"
    border = "#30363d" if dark else "#d0d7de"
    text = "#c9d1d9" if dark else "#24292f"

    # Match the old summary-card structure:
    # title on top, legend on the left, donut chart on the right.
    lines: list[str] = []
    lines.append('<svg xmlns="http://www.w3.org/2000/svg" width="340" height="200" viewBox="0 0 340 200">')
    lines.append('<style>* { font-family: "Garamond Libre Profile Cards", "Garamond Libre", Georgia, serif; }</style>')
    lines.append(f'<rect x="1" y="1" rx="5" ry="5" height="198" width="338" stroke="{border}" stroke-width="1" fill="{bg}" stroke-opacity="1"/>')
    title_style = get_profile_title_style(dark)
    # The profile card is rendered as 700px viewBox at 80% README width.
    # Language cards are rendered as 340px viewBox at 40.5% README width.
    # Match the final on-page title size, not only the raw SVG font-size.
    title_style = title_style.replace("font-size: 22px", "font-size: 18px")
    lines.append(f'<text x="30" y="40" style="{title_style}">{xml_escape(title)}</text>')

    if not items or total <= 0:
        lines.append(f'<text x="40" y="95" style="fill: {text}; font-size: 14px;">No data yet</text>')
        lines.append("</svg>")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    legend_x = 40
    legend_y = 70
    row_gap = 22

    for i, (language, _) in enumerate(items):
        y = legend_y + i * row_gap
        color = LANG_COLORS.get(language, LANG_COLORS["Other"])
        lines.append(f'<rect x="{legend_x}" y="{y - 10}" width="14" height="14" rx="2" fill="{color}" stroke="{border}" style="stroke-width: 1px;"/>')
        lines.append(f'<text x="{legend_x + 22}" y="{y + 2}" style="fill: {text}; font-size: 14px;">{xml_escape(language)}</text>')

    cx = 238
    cy = 112
    r_outer = 58
    r_inner = 34
    angle = -math.pi / 2

    for language, value in items:
        color = LANG_COLORS.get(language, LANG_COLORS["Other"])
        next_angle = angle + math.tau * (value / total)
        path_data = donut_arc_path(cx, cy, r_outer, r_inner, angle, next_angle)
        lines.append(f'<path d="{path_data}" style="fill: {color}; stroke-width: 2px;" stroke="{border}"/>')
        angle = next_angle

    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def main() -> None:
    external = external_contribution_languages()
    own = own_repository_languages()

    write_svg(OUT_DIR / "external-contribution-languages-light.svg", "External PR Languages", external, dark=False)
    write_svg(OUT_DIR / "external-contribution-languages-dark.svg", "External PR Languages", external, dark=True)
    write_svg(OUT_DIR / "own-repository-languages-light.svg", "Own Repo Languages", own, dark=False)
    write_svg(OUT_DIR / "own-repository-languages-dark.svg", "Own Repo Languages", own, dark=True)

    print("external contribution languages:", dict(external.most_common()))
    print("own repository languages:", dict(own.most_common()))


if __name__ == "__main__":
    main()
