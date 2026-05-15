from __future__ import annotations

import json
import math
import os
import re
import ssl
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
LINGUIST_LANGUAGES_URL = "https://raw.githubusercontent.com/github-linguist/linguist/main/lib/linguist/languages.yml"
OTHER_COLOR = "#6e7681"

# GitHub Linguist has ambiguous extensions. For this profile card, we want
# common source/document suffix semantics: .md means Markdown, not GCC MD.
EXTENSION_OVERRIDES = {
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".mdown": "Markdown",
    ".mkd": "Markdown",
    ".mkdn": "Markdown",
    ".cu": "Cuda",
    ".cuh": "Cuda",
}

TOKEN = (
    os.environ.get("GITHUB_TOKEN")
    or os.environ.get("GH_TOKEN")
    or os.environ.get("SUMMARY_GITHUB_TOKEN")
)

OUT_DIR = Path("assets")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "LwhJesse-profile-language-cards",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    return headers


def request_bytes(url: str, headers: dict[str, str] | None = None, retries: int = 4) -> tuple[bytes, dict[str, str]]:
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, headers=headers or {"User-Agent": "LwhJesse-profile-language-cards"})

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read(), dict(resp.headers)
        except (urllib.error.URLError, TimeoutError, ssl.SSLError, ConnectionResetError) as error:
            last_error = error
            if attempt < retries:
                time.sleep(1.5 * attempt)
                continue
            raise RuntimeError(f"request failed after {retries} attempts: {url}\n{error}") from error

    raise RuntimeError(f"request failed: {url}\n{last_error}")


def request_text(url: str, headers: dict[str, str] | None = None) -> str:
    body, _ = request_bytes(url, headers=headers)
    return body.decode("utf-8")


def request_json(url: str) -> tuple[Any, dict[str, str]]:
    body, headers = request_bytes(url, headers=github_headers())
    return json.loads(body.decode("utf-8")), headers


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


def yaml_scalar(value: str) -> str:
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    return value


def parse_linguist_languages(text: str) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    languages: dict[str, dict[str, Any]] = {}
    current: str | None = None
    section: str | None = None

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.startswith("#") or raw_line == "---":
            continue

        language_match = re.match(r"^([^ \t][^:\n]*):\s*$", raw_line)
        if language_match:
            current = language_match.group(1)
            languages[current] = {
                "extensions": [],
                "filenames": [],
                "color": None,
                "group": None,
            }
            section = None
            continue

        if current is None:
            continue

        stripped = raw_line.strip()

        if stripped == "extensions:":
            section = "extensions"
            continue

        if stripped == "filenames:":
            section = "filenames"
            continue

        if re.match(r"^[A-Za-z_][A-Za-z0-9_ -]*:", stripped):
            section = None

            if stripped.startswith("color:"):
                languages[current]["color"] = yaml_scalar(stripped.split(":", 1)[1])

            if stripped.startswith("group:"):
                languages[current]["group"] = yaml_scalar(stripped.split(":", 1)[1])

            continue

        if section in {"extensions", "filenames"} and stripped.startswith("- "):
            languages[current][section].append(yaml_scalar(stripped[2:]))

    colors: dict[str, str] = {}
    for language, meta in languages.items():
        color = meta.get("color")
        if color:
            colors[language] = color

    for language, meta in languages.items():
        if language in colors:
            continue
        group = meta.get("group")
        if group and group in colors:
            colors[language] = colors[group]

    extension_language: dict[str, str] = {}
    filename_language: dict[str, str] = {}

    for language, meta in languages.items():
        for extension in meta["extensions"]:
            extension_language.setdefault(extension, language)

        for filename in meta["filenames"]:
            filename_language.setdefault(filename, language)

    return extension_language, filename_language, colors


_LINGUIST_DATA: tuple[dict[str, str], dict[str, str], dict[str, str]] | None = None


def linguist_data() -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    global _LINGUIST_DATA

    if _LINGUIST_DATA is None:
        text = request_text(LINGUIST_LANGUAGES_URL)
        _LINGUIST_DATA = parse_linguist_languages(text)

    return _LINGUIST_DATA


def language_from_filename(filename: str) -> str:
    extension_language, filename_language, _ = linguist_data()

    base = Path(filename).name
    if base in filename_language:
        return filename_language[base]

    for extension, language in sorted(EXTENSION_OVERRIDES.items(), key=lambda item: len(item[0]), reverse=True):
        if filename.endswith(extension):
            return language

    for extension in sorted(extension_language, key=len, reverse=True):
        if filename.endswith(extension):
            return extension_language[extension]

    return "Other"


def language_color(language: str) -> str:
    if language == "Other":
        return OTHER_COLOR

    _, _, colors = linguist_data()
    return colors.get(language, OTHER_COLOR)


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
                continue

            stats[language] += changes

    return stats


def count_text_lines(body: bytes) -> int | None:
    if not body:
        return 0

    if b"\0" in body[:4096]:
        return None

    return body.count(b"\n") + (0 if body.endswith(b"\n") else 1)


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

        default_branch = repo.get("default_branch")
        if not default_branch:
            continue

        tree_ref = urllib.parse.quote(default_branch, safe="")
        tree, _ = request_json(f"{API}/repos/{USER}/{name}/git/trees/{tree_ref}?recursive=1")

        for item in tree.get("tree", []):
            if item.get("type") != "blob":
                continue

            file_path = str(item.get("path", ""))
            language = language_from_filename(file_path)

            branch_url = urllib.parse.quote(default_branch, safe="")
            path_url = urllib.parse.quote(file_path, safe="/")
            raw_url = f"https://raw.githubusercontent.com/{USER}/{name}/{branch_url}/{path_url}"

            body, _ = request_bytes(raw_url)
            line_count = count_text_lines(body)

            if line_count is None or line_count <= 0:
                continue

            stats[language] += line_count

    return stats


def get_profile_title_style(dark: bool) -> str:
    svg_path = Path(
        "profile-summary-card-output/github_dark/0-profile-details.svg"
        if dark
        else "profile-summary-card-output/github/0-profile-details.svg"
    )
    root = ET.fromstring(svg_path.read_text(encoding="utf-8"))

    for elem in root.iter():
        if elem.tag.endswith("text") and (elem.text or "").strip() == USER:
            style = elem.attrib.get("style", "").strip()
            if style:
                return style

    raise RuntimeError(f"Could not find title style for {USER} in {svg_path}")


def display_language_name(language: str, max_chars: int = 18) -> str:
    if len(language) <= max_chars:
        return language
    return language[: max_chars - 1] + "…"


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

    lines: list[str] = []
    lines.append('<svg xmlns="http://www.w3.org/2000/svg" width="340" height="200" viewBox="0 0 340 200">')
    lines.append('<style>* { font-family: "Garamond Libre Profile Cards", "Garamond Libre", Georgia, serif; }</style>')
    lines.append(f'<rect x="1" y="1" rx="5" ry="5" height="198" width="338" stroke="{border}" stroke-width="1" fill="{bg}" stroke-opacity="1"/>')

    title_style = get_profile_title_style(dark)
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
        color = language_color(language)

        lines.append(f'<rect x="{legend_x}" y="{y - 10}" width="14" height="14" rx="2" fill="{color}" stroke="{border}" style="stroke-width: 1px;"/>')
        label = display_language_name(language)
        lines.append(f'<text x="{legend_x + 22}" y="{y + 2}" style="fill: {text}; font-size: 14px;">{xml_escape(label)}</text>')

    cx = 238
    cy = 112
    r_outer = 58
    r_inner = 34
    angle = -math.pi / 2

    for language, value in items:
        color = language_color(language)
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
