# AA Leaderboards

[![Daily Fetch](https://github.com/garo-pro/aa-leaderboards/actions/workflows/fetch.yml/badge.svg)](https://github.com/garo-pro/aa-leaderboards/actions/workflows/fetch.yml)

Daily snapshots of [Artificial Analysis](https://artificialanalysis.ai) leaderboard data, published as readable Markdown tables.

Forked from [oolong-tea-2026/artificial-analysis-leaderboards](https://github.com/oolong-tea-2026/artificial-analysis-leaderboards), restructured to publish Markdown tables instead of dated JSON history.

## Tables

The current snapshot, rendered as Markdown:

| Endpoint | Description | Table |
|----------|-------------|-------|
| `llms` | LLM leaderboard | [tables/llms.md](tables/llms.md) |
| `text-to-image` | Text-to-image arena rankings | [tables/text-to-image.md](tables/text-to-image.md) |
| `image-editing` | Image editing arena rankings | [tables/image-editing.md](tables/image-editing.md) |
| `text-to-speech` | Text-to-speech arena rankings | [tables/text-to-speech.md](tables/text-to-speech.md) |
| `text-to-video` | Text-to-video arena rankings | [tables/text-to-video.md](tables/text-to-video.md) |
| `image-to-video` | Image-to-video arena rankings | [tables/image-to-video.md](tables/image-to-video.md) |

See also the [tables index](tables/README.md).

## Sources

This repo intentionally avoids relying on the rate-limited free AA API for daily full snapshots.

Instead it collects from Artificial Analysis public web surfaces:

- `llms` → `https://artificialanalysis.ai/leaderboards/models`
- `text-to-image` → `https://artificialanalysis.ai/api/text-to-image/arena/preferences?supports_image_input=false`
- `image-editing` → `https://artificialanalysis.ai/api/text-to-image/arena/preferences?supports_image_input=true`
- `text-to-speech` → `https://artificialanalysis.ai/api/text-to-speech/arena/preferences`
- `text-to-video` → `https://artificialanalysis.ai/api/text-to-video/arena/preferences?supports-image-input=false`
- `image-to-video` → `https://artificialanalysis.ai/api/text-to-video/arena/preferences?supports-image-input=true`

## Structure

```text
internal/               # Internal, machine-readable data — implementation detail, not the published product
├── _index.json          # Daily fetch summary
├── llms.json
├── text-to-image.json
├── image-editing.json
├── text-to-speech.json
├── text-to-video.json
└── image-to-video.json

tables/                 # Published output — Markdown tables rendered from internal/
├── README.md            # Table index
├── llms.md
├── text-to-image.md
├── image-editing.md
├── text-to-speech.md
├── text-to-video.md
└── image-to-video.md
```

Unlike the upstream repo, this fork keeps only the **current** snapshot — `internal/*.json` and `tables/*.md` are overwritten in place on each run, no dated history is retained.

Each `internal/*.json` file includes:

- `meta.endpoint`
- `meta.source_type`
- `meta.source_url`
- `meta.parser_version`
- `meta.fetched_at`
- `meta.model_count`

## Pipeline

Two scripts run in sequence, both on the same daily schedule:

1. `scripts/fetch_leaderboards.py` — fetches the public web surfaces above and writes the normalized current snapshot to `internal/*.json`.
2. `scripts/render_tables.py` — reads `internal/*.json` and renders full-detail Markdown tables to `tables/*.md`.

```bash
python3 scripts/fetch_leaderboards.py
python3 scripts/render_tables.py
```

## Updates

Data is fetched and tables are re-rendered daily at 05:13 UTC via GitHub Actions.

## Attribution

Data provided by [Artificial Analysis](https://artificialanalysis.ai). Please provide attribution when reusing the data. See their [methodology](https://artificialanalysis.ai/methodology) for benchmark details.

## License

MIT — Data attribution to Artificial Analysis required.
