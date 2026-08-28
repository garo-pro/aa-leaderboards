#!/usr/bin/env python3
"""
Render the internal/ leaderboard JSON snapshots into readable Markdown tables
under tables/. This is the second stage of the pipeline: fetch_leaderboards.py
writes the machine-readable internal/*.json, this script turns that into the
human-facing docs the README links to.

Usage:
  python3 scripts/render_tables.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SLUGS = [
    "llms",
    "text-to-image",
    "image-editing",
    "text-to-speech",
    "text-to-video",
    "image-to-video",
]

ATTRIBUTION = "Data by [Artificial Analysis](https://artificialanalysis.ai/), via their [Data API](https://artificialanalysis.ai/data-api)."

TITLES = {
    "llms": "LLM Leaderboard",
    "text-to-image": "Text-to-Image Arena",
    "image-editing": "Image Editing Arena",
    "text-to-speech": "Text-to-Speech Arena",
    "text-to-video": "Text-to-Video Arena",
    "image-to-video": "Image-to-Video Arena",
}


def flatten(obj: Any, prefix: str = "", out: dict[str, Any] | None = None) -> dict[str, Any]:
    """Flatten nested dicts into dotted-path columns. Lists become compact JSON strings."""
    if out is None:
        out = {}
    if isinstance(obj, dict):
        for key, value in obj.items():
            flatten(value, f"{prefix}.{key}" if prefix else key, out)
    elif isinstance(obj, list):
        out[prefix] = json.dumps(obj, separators=(",", ":"), ensure_ascii=False) if obj else ""
    else:
        out[prefix] = obj
    return out


def cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, float):
        text = f"{value:.6g}"
    else:
        text = str(value)
    return text.replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def render_table(columns: list[str], rows: list[dict[str, Any]]) -> str:
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, divider]
    for row in rows:
        lines.append("| " + " | ".join(cell(row.get(col)) for col in columns) + " |")
    return "\n".join(lines)


def render_source(internal_dir: Path, tables_dir: Path, slug: str) -> str | None:
    src_path = internal_dir / f"{slug}.json"
    if not src_path.exists():
        return None

    with open(src_path, encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("meta", {})
    models = data.get("models", [])
    flat_rows = [flatten(model) for model in models]

    columns: list[str] = []
    seen = set()
    for row in flat_rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                columns.append(key)

    title = TITLES.get(slug, slug)
    lines = [
        f"# {title}",
        "",
        ATTRIBUTION,
        "",
        f"- Source: [{meta.get('source_url', '')}]({meta.get('source_url', '')})",
        f"- Fetched at: {meta.get('fetched_at', 'unknown')}",
        f"- Model count: {meta.get('model_count', len(models))}",
        "",
        "> Generated from `internal/" + f"{slug}.json" + "` by `scripts/render_tables.py`. Do not edit by hand.",
        "",
    ]

    if flat_rows:
        lines.append(render_table(columns, flat_rows))
    else:
        lines.append("_No data available for this endpoint in the current snapshot._")
    lines.append("")
    lines.append("---")
    lines.append(ATTRIBUTION)
    lines.append("")

    out_path = tables_dir / f"{slug}.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return meta.get("fetched_at")


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    internal_dir = repo_root / "internal"
    tables_dir = repo_root / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    fetched_at = None
    rendered = []
    for slug in SLUGS:
        result = render_source(internal_dir, tables_dir, slug)
        if result is not None:
            rendered.append(slug)
            fetched_at = fetched_at or result

    index_lines = [
        "# Leaderboard Tables",
        "",
        ATTRIBUTION,
        "",
        f"Snapshot fetched at: {fetched_at or 'unknown'}",
        "",
        "| Leaderboard | Table |",
        "|---|---|",
    ]
    for slug in rendered:
        index_lines.append(f"| {TITLES.get(slug, slug)} | [{slug}.md]({slug}.md) |")
    index_lines.append("")
    index_lines.append(
        "Same data, grouped by provider instead of endpoint: [endpoint-providers.md](endpoint-providers.md)."
    )
    index_lines.append("")

    with open(tables_dir / "README.md", "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines))

    print(f"Rendered {len(rendered)} table(s) to {tables_dir}/")


if __name__ == "__main__":
    main()
