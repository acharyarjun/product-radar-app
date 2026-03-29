# GitHub Actions: secrets and variables

Configure these in the repository: **Settings → Secrets and variables → Actions**.

## Secrets (sensitive)

| Name | Purpose |
|------|---------|
| `NOTION_TOKEN` | Internal integration secret from [Notion integrations](https://www.notion.so/my-integrations). |
| `NOTION_DATABASE_ID` | UUID of your **Product candidates** database (from the database URL). |
| `ALIEXPRESS_AFFILIATE_KEY` | Optional; reserved for future affiliate/API use. |

## Variables (non-secret, optional)

| Name | Example | Purpose |
|------|---------|---------|
| `NOTION_ENABLED` | `true` | When set, merged into config so Notion registration runs in CI without editing `config.yaml`. |

## Local development

Copy `.env.example` to `.env` and fill values. The app reads these via `pydantic-settings`.

## Notion database properties

Create a Notion database whose **property names** match `config.yaml` under `notion.property_names` (defaults listed there). Types:

- **Name** — Title  
- **Source**, **Competition**, **Viability**, **Category**, **Notes**, **Pipeline status**, **Target** — Text (rich text)  
- **Source URL** — URL  
- **Source price EUR**, **Recommended sale EUR**, **Margin pct**, **Demand** — Number  
- **Run date** — Date  

Connect your integration to the database (**⋯ → Connections**).

## Optional digest page

In `config.yaml`, set `notion.digest_parent_page_id` to a page UUID where summary pages should appear, and ensure the integration can access that page. Use `notion.digest_page_title_property` if Notion expects a different title property name than `title`.
