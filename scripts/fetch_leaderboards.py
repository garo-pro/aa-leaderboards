#!/usr/bin/env python3
"""
Fetch Artificial Analysis leaderboard data from the official Data API (Free tier).
Saves the current snapshot to internal/ (overwritten each run — no history is kept
here; run scripts/render_tables.py afterwards to publish readable Markdown tables).

Requires an API key: sign up for a free key at https://artificialanalysis.ai/data-api
and set it as the AA_API_KEY environment variable. Free tier allows 100 requests per
24h; this script uses at most a handful per run.

Sources (all under https://artificialanalysis.ai/api/v2, Free tier):
  - /language/models/free                    → LLM leaderboard (paginated)
  - /media/text-to-image/models/free         → Text-to-image arena Elo
  - /media/image-editing/models/free         → Image editing arena Elo
  - /media/text-to-speech/models/free        → Text-to-speech arena Elo
  - /media/text-to-video/models/free         → Text-to-video arena Elo
  - /media/image-to-video/models/free        → Image-to-video arena Elo

Usage:
  AA_API_KEY=... python3 scripts/fetch_leaderboards.py
  AA_API_KEY=... python3 scripts/fetch_leaderboards.py --only llms text-to-video
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import urllib.error
import urllib.request

API_BASE = "https://artificialanalysis.ai/api/v2"
PARSER_VERSION = "official-api-v1"

SOURCES = [
    {
        "slug": "llms",
        "path": "/language/models/free",
        "kind": "language",
        "description": "LLM leaderboard (Free tier)",
    },
    {
        "slug": "text-to-image",
        "path": "/media/text-to-image/models/free",
        "kind": "media",
        "description": "Text-to-image arena Elo rankings (Free tier)",
    },
    {
        "slug": "image-editing",
        "path": "/media/image-editing/models/free",
        "kind": "media",
        "description": "Image editing arena Elo rankings (Free tier)",
    },
    {
        "slug": "text-to-speech",
        "path": "/media/text-to-speech/models/free",
        "kind": "media",
        "description": "Text-to-speech arena Elo rankings (Free tier)",
    },
    {
        "slug": "text-to-video",
        "path": "/media/text-to-video/models/free",
        "kind": "media",
        "description": "Text-to-video arena Elo rankings (Free tier)",
    },
    {
        "slug": "image-to-video",
        "path": "/media/image-to-video/models/free",
        "kind": "media",
        "description": "Image-to-video arena Elo rankings (Free tier)",
    },
]


def fetch_json(path: str, api_key: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    url = API_BASE + path
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"

    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "x-api-key": api_key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e


def normalize_llm(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": raw.get("id"),
        "name": raw.get("name"),
        "slug": raw.get("slug"),
        "release_date": raw.get("release_date"),
        "creator": raw.get("model_creator"),
        "evaluations": raw.get("evaluations"),
        "intelligence_index_cost": raw.get("artificial_analysis_intelligence_index_cost"),
        "pricing": raw.get("pricing"),
        "performance": raw.get("performance"),
    }


def normalize_media(raw: dict[str, Any]) -> dict[str, Any]:
    ci_95 = raw.get("ci_95")
    return {
        "id": raw.get("id"),
        "name": raw.get("name"),
        "slug": raw.get("slug"),
        "creator": raw.get("model_creator"),
        "elo": raw.get("elo"),
        "ci_95": ci_95,
        "ci95_range": f"-{ci_95}/+{ci_95}" if ci_95 is not None else None,
    }


def fetch_language_models(api_key: str) -> list[dict[str, Any]]:
    models: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = fetch_json("/language/models/free", api_key, params={"page": page})
        models.extend(payload.get("data", []))
        pagination = payload.get("pagination") or {}
        if not pagination.get("has_more"):
            break
        page += 1
    return [normalize_llm(m) for m in models]


def fetch_media_models(path: str, api_key: str) -> list[dict[str, Any]]:
    payload = fetch_json(path, api_key)
    return [normalize_media(m) for m in payload.get("data", [])]


def fetch_source(source: dict[str, str], api_key: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    slug = source["slug"]
    if source["kind"] == "language":
        models = fetch_language_models(api_key)
    else:
        models = fetch_media_models(source["path"], api_key)

    meta = {
        "endpoint": slug,
        "source_type": "official_api_free_tier",
        "source_url": API_BASE + source["path"],
        "source_description": source["description"],
        "parser_version": PARSER_VERSION,
        "model_count": len(models),
    }
    return models, meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Artificial Analysis leaderboards")
    parser.add_argument("--only", nargs="*", help="Only fetch these endpoint slugs")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests in seconds")
    args = parser.parse_args()

    api_key = os.environ.get("AA_API_KEY")
    if not api_key:
        print("ERROR: AA_API_KEY environment variable is not set.", file=sys.stderr)
        print("Get a free key at https://artificialanalysis.ai/data-api", file=sys.stderr)
        sys.exit(1)

    sources = SOURCES
    if args.only:
        wanted = set(args.only)
        sources = [source for source in SOURCES if source["slug"] in wanted]
        if not sources:
            print(f"ERROR: No matching endpoints for {args.only}", file=sys.stderr)
            sys.exit(1)

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    fetched_at = now.isoformat()

    internal_dir = repo_root / "internal"
    internal_dir.mkdir(parents=True, exist_ok=True)

    index_path = internal_dir / "_index.json"
    if index_path.exists() and args.only:
        with open(index_path, encoding="utf-8") as f:
            index = json.load(f)
        index["fetched_at"] = fetched_at
    else:
        index = {
            "date": date_str,
            "fetched_at": fetched_at,
            "source": "https://artificialanalysis.ai/data-api",
            "source_type": "official_api_free_tier",
            "parser_version": PARSER_VERSION,
            "endpoints": {},
        }

    success_count = 0
    total = len(sources)

    for i, source in enumerate(sources, start=1):
        slug = source["slug"]
        print(f"Fetching {slug}...", end=" ", flush=True)
        try:
            models, meta = fetch_source(source, api_key)
            meta["fetched_at"] = fetched_at
            output = {
                "meta": meta,
                "models": models,
            }

            out_path = internal_dir / f"{slug}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)

            index["endpoints"][slug] = {
                "model_count": len(models),
                "source_type": "official_api_free_tier",
                "source_url": API_BASE + source["path"],
            }
            success_count += 1
            print(f"✓ {len(models)} models")
        except Exception as e:
            print(f"✗ {e}", file=sys.stderr)
            index["endpoints"][slug] = {
                "error": str(e),
                "source_type": "official_api_free_tier",
                "source_url": API_BASE + source["path"],
            }

        if i < total:
            time.sleep(args.delay)

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print(f"\nDone: {success_count}/{total} endpoints, saved to internal/")
    if success_count < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
