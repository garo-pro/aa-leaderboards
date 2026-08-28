#!/usr/bin/env python3
"""
Render the internal/ leaderboard JSON snapshots into a single Markdown doc
grouped by provider (creator), instead of by endpoint. This is an alternate
view of the same data rendered by render_tables.py: one heading per provider,
with a table of every model from that provider across all endpoints.

Usage:
  python3 scripts/render_by_provider.py
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


def load_rows(internal_dir: Path) -> tuple[list[tuple[str, dict[str, Any]]], str | None]:
    """Return (provider_name, flattened_row) for every model across all endpoints, in
    endpoint order, plus the newest fetched_at timestamp seen."""
    all_rows: list[tuple[str, dict[str, Any]]] = []
    fetched_at = None

    for slug in SLUGS:
        src_path = internal_dir / f"{slug}.json"
        if not src_path.exists():
            continue

        with open(src_path, encoding="utf-8") as f:
            data = json.load(f)

        meta = data.get("meta", {})
        fetched_at = fetched_at or meta.get("fetched_at")

        for model in data.get("models", []):
            provider = ((model.get("creator") or {}).get("name")) or "Unknown"
            flat = flatten(model)
            flat.pop("creator.name", None)
            flat.pop("creator.id", None)
            flat["endpoint"] = TITLES.get(slug, slug)
            all_rows.append((provider, flat))

    return all_rows, fetched_at


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    internal_dir = repo_root / "internal"
    tables_dir = repo_root / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    all_rows, fetched_at = load_rows(internal_dir)

    by_provider: dict[str, list[dict[str, Any]]] = {}
    for provider, flat in all_rows:
        by_provider.setdefault(provider, []).append(flat)

    lines = [
        "# Endpoint Providers",
        "",
        ATTRIBUTION,
        "",
        f"Snapshot fetched at: {fetched_at or 'unknown'}",
        f"- Provider count: {len(by_provider)}",
        f"- Model count: {len(all_rows)}",
        "",
        "> Generated from `internal/*.json` by `scripts/render_by_provider.py`. Do not edit by hand.",
        "",
    ]

    for provider in sorted(by_provider, key=str.casefold):
        rows = by_provider[provider]

        columns: list[str] = ["endpoint"]
        seen = {"endpoint"}
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    columns.append(key)

        lines.append(f"## {provider}")
        lines.append("")
        lines.append(f"Model count: {len(rows)}")
        lines.append("")
        lines.append(render_table(columns, rows))
        lines.append("")

    lines.append("---")
    lines.append(ATTRIBUTION)
    lines.append("")

    out_path = tables_dir / "endpoint-providers.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Rendered {len(by_provider)} provider section(s) to {out_path}")


if __name__ == "__main__":
    main()
