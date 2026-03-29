# Product Radar

Daily **market-research agent** for a Bilbao / Spain-focused resale business: discover supplier products (AliExpress, optional Temu), benchmark Amazon.es and Google Trends, score viability, write Markdown + CSV, persist to SQLite, and **register new candidates in a Notion database**.

The storefront (Shopify or your own site) is separate; Notion is your **review queue** before listing.

## Quick start

```bash
pip install -e ".[dev]"
copy .env.example .env   # Windows: copy; then edit .env
python -m src.main
```

Or: `product-radar` (console script from `pyproject.toml`).

### Schedule (local)

```bash
python -m src.main --schedule
```

Uses `schedule.daily_run_time` and `schedule.timezone` from `config.yaml`.

## Configuration

- **`config.yaml`** — thresholds, categories, sources, Notion property names, paths.
- **`.env`** — secrets (never commit). See [`.env.example`](.env.example).
- **GitHub Actions** — add the same values as **Secrets** / **Variables**; see [`docs/GITHUB_SECRETS.md`](docs/GITHUB_SECRETS.md).

### Environment variables (GitHub & local)

| Variable | Type | Description |
|----------|------|-------------|
| `NOTION_TOKEN` | Secret | Notion internal integration token. |
| `NOTION_DATABASE_ID` | Secret | Target database UUID. |
| `NOTION_ENABLED` | Variable | `true` / `false` overrides `config.yaml` `notion.enabled`. |
| `ALIEXPRESS_AFFILIATE_KEY` | Secret | Optional; reserved for future use. |
| `RADAR_GIT_AUTO_COMMIT` | Variable | `true`/`false` overrides git auto-commit (local runs). |
| `RADAR_GIT_AUTO_PUSH` | Variable | `true`/`false` overrides git auto-push. |

## Notion database

Create properties matching `notion.property_names` in `config.yaml` (defaults: Name, Source, Source URL, prices, Margin pct, Demand, Competition, Viability, Category, Run date, Notes, Pipeline status, Target). Types are documented in [`docs/GITHUB_SECRETS.md`](docs/GITHUB_SECRETS.md).

Enable Notion in `config.yaml` (`notion.enabled: true`) or set `NOTION_ENABLED=true` in GitHub Variables.

## CI

Workflow [`.github/workflows/daily-radar.yml`](.github/workflows/daily-radar.yml) runs daily (06:00 UTC) or on demand. It commits `reports/*.md`, `reports/*.csv`, and `memory.json` when there are changes.

## Tests

```bash
pytest tests -v
```

## Limitations

AliExpress and Amazon may block automated requests; the pipeline degrades gracefully (empty discovery, logged errors). Optional affiliate/API keys can improve reliability later.

Full architecture: [`instructions.md`](instructions.md).