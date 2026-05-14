from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
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


def xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def top_items(stats: Counter[str], limit: int = 6) -> list[tuple[str, int]]:
    return [(language, value) for language, value in stats.most_common(limit) if value > 0]


def write_svg(path: Path, title: str, stats: Counter[str], dark: bool) -> None:
    items = top_items(stats)
    total = sum(value for _, value in items)

    bg = "#0d1117" if dark else "#ffffff"
    border = "#30363d" if dark else "#d0d7de"
    text = "#c9d1d9" if dark else "#24292f"
    muted = "#8b949e" if dark else "#57606a"

    lines: list[str] = []
    lines.append('<svg xmlns="http://www.w3.org/2000/svg" width="340" height="200" viewBox="0 0 340 200">')
    lines.append("<style>*{font-family:Georgia,serif}</style>")
    lines.append(f'<rect x="1" y="1" rx="6" ry="6" width="338" height="198" fill="{bg}" stroke="{border}"/>')
    lines.append(f'<text x="24" y="35" font-size="20" font-weight="600" fill="{text}">{xml_escape(title)}</text>')

    if not items or total <= 0:
        lines.append(f'<text x="24" y="95" font-size="14" fill="{muted}">No data yet</text>')
    else:
        max_value = max(value for _, value in items)
        y = 60

        for language, value in items:
            color = LANG_COLORS.get(language, LANG_COLORS["Other"])
            percent = value / total * 100
            bar_width = max(4, int(150 * value / max_value))

            lines.append(f'<rect x="24" y="{y - 10}" width="10" height="10" rx="2" fill="{color}"/>')
            lines.append(f'<text x="42" y="{y}" font-size="13" fill="{text}">{xml_escape(language)}</text>')
            lines.append(f'<rect x="155" y="{y - 10}" width="150" height="10" rx="4" fill="{border}"/>')
            lines.append(f'<rect x="155" y="{y - 10}" width="{bar_width}" height="10" rx="4" fill="{color}"/>')
            lines.append(f'<text x="312" y="{y}" font-size="12" text-anchor="end" fill="{muted}">{percent:.1f}%</text>')

            y += 22

    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    external = external_contribution_languages()
    own = own_repository_languages()

    write_svg(OUT_DIR / "external-contribution-languages-light.svg", "External Contribution Languages", external, dark=False)
    write_svg(OUT_DIR / "external-contribution-languages-dark.svg", "External Contribution Languages", external, dark=True)
    write_svg(OUT_DIR / "own-repository-languages-light.svg", "Own Repository Languages", own, dark=False)
    write_svg(OUT_DIR / "own-repository-languages-dark.svg", "Own Repository Languages", own, dark=True)

    print("external contribution languages:", dict(external.most_common()))
    print("own repository languages:", dict(own.most_common()))


if __name__ == "__main__":
    main()
