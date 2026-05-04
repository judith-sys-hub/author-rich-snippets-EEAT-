# Author Rich Snippets — E-E-A-T Profile Pipeline

An automated pipeline that scrapes author profiles from a news website, generates AI-powered bios, and produces structured **Schema.org JSON-LD Rich Snippets** (Person + NewsArticle) ready for CMS integration.

Built for [Kleine Zeitung](https://www.kleinezeitung.at) as part of an E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness) initiative — but designed to be **reusable by any news organisation**.

---

## What It Does

```
Discover authors → Scrape profiles → Enrich data → Generate bios → Render JSON-LD → Editorial review → CMS import
```

1. **Discover** — finds all active author profile pages
2. **Scrape** — extracts name, title, bio, photo, article history (2025–2026 only, max 15 articles)
3. **Enrich** — adds Wikipedia summary, social links (LinkedIn, Bluesky, Twitter, Instagram)
4. **Generate** — writes an E-E-A-T-optimised bio using the Claude API (Anthropic)
5. **Render** — produces a `Schema.org` JSON-LD file per author
6. **Review** — exports a formatted Excel file for editorial sign-off; imports approved edits back
7. **Import** — approved bios and beats update the author JSON and re-render the Rich Snippet

---

## Prerequisites

- Python 3.11+
- A subscription login for the target news site (used by the scraper)
- An [Anthropic API key](https://console.anthropic.com/) for bio generation
- [Playwright](https://playwright.dev/python/) browser drivers

---

## Installation

```bash
git clone https://github.com/judith-sys-hub/author-rich-snippets-EEAT-
cd author-rich-snippets-EEAT-

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
playwright install chromium
```

---

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```env
KLZ_USERNAME=your.email@kleinezeitung.at
KLZ_PASSWORD=your_password
KLZ_LOGIN_URL=https://abo.kleinezeitung.at/
KLZ_BASE_URL=https://www.kleinezeitung.at
SCRAPE_DELAY_SECONDS=2
ANTHROPIC_API_KEY=your_anthropic_api_key
```

> **Never commit `.env`** — it is gitignored. The `session.json` browser cookie file is also gitignored.

---

## Running the Pipeline

### Full run (all stages)

```bash
python pipeline.py
```

### Single stage

```bash
python pipeline.py --stage discover
python pipeline.py --stage scrape
python pipeline.py --stage enrich
python pipeline.py --stage generate
python pipeline.py --stage render
```

### Useful flags

```bash
python pipeline.py --limit 5          # process only 5 authors (great for testing)
python pipeline.py --dry-run          # log actions without writing files
python pipeline.py --stage render --limit 3
```

The pipeline is **incremental** — it tracks each author's stage in `pipeline.db` (SQLite) and skips authors that have already completed a stage. Re-running is safe.

---

## Pipeline Stages in Detail

| Stage | Input | Output |
|---|---|---|
| `discover` | Author listing pages | Author slugs + names in `pipeline.db` |
| `scrape` | Author profile pages | `data/authors/{slug}.json` |
| `enrich` | Author JSON | Wikipedia summary, social links added to JSON |
| `generate` | Author JSON | AI-generated bio (`bio_generated`) added to JSON |
| `render` | Author JSON | `richsnippet/{slug}.json` (Schema.org JSON-LD) |

---

## Editorial Review Workflow

After `render`, the pipeline produces 231 author profiles ready for editorial sign-off.

### Step 1 — Export

```bash
python -m review.export
```

Creates `review/author_review.xlsx` (gitignored).

**Share it with your colleagues** via Google Drive, SharePoint, or email — whichever your team uses. The file opens directly in Google Sheets (File → Import is not needed; just upload and open). Editors do not need to install anything.

> The file is gitignored and never committed to the repository, so sharing it manually is always required.

The file has:
- **Row 1** — live progress summary with COUNTIF formulas (updates as editors type)
- **Row 2** — frozen header row
- **Rows 3+** — one author per row

| Column | Content | Editable? |
|---|---|---|
| slug | Author identifier | No — needed by importer |
| name | Full name | No |
| status | `pending` / `approved` / `flagged` | **Yes** — dropdown |
| bio | AI-generated bio | **Yes** — edit directly |
| themen | Topic beats, semicolon-separated | **Yes** — e.g. `Sport; GAK; Europa League` |

Status column is colour-coded: green = approved, yellow = pending, red = flagged.

### Step 2 — Editors review

For each row, editors set the status dropdown:
- `approved` — bio and beats look good (or have been corrected inline)
- `flagged` — needs further research, will be logged and skipped
- `pending` — not reviewed yet, will be silently skipped

### Step 3 — Import

Save the file as `.xlsx` and place it back in the `review/` folder, then run:

```bash
python -m review.importer
```

This:
- Updates `data/authors/{slug}.json` for any approved rows where bio or beats changed
- Re-renders `richsnippet/{slug}.json` for changed authors
- Advances the author's pipeline stage to `reviewed`
- Lists all flagged authors at the end

---

## Output Format

Each author produces a `richsnippet/{slug}.json` file:

```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Person",
      "@id": "https://www.kleinezeitung.at/autor/1/peter-altmann",
      "name": "Peter Altmann",
      "jobTitle": "Sport",
      "description": "Peter Altmann ist Sportredakteur bei der Kleinen Zeitung...",
      "image": "https://img.kleinezeitung.at/...",
      "url": "https://www.kleinezeitung.at/autor/1/peter-altmann",
      "worksFor": {
        "@type": "NewsMediaOrganization",
        "@id": "https://www.kleinezeitung.at",
        "name": "Kleine Zeitung"
      },
      "knowsAbout": ["Österreichischer Fußball", "GAK", "SK Sturm Graz"]
    },
    {
      "@type": "NewsArticle",
      "headline": "...",
      "url": "...",
      "datePublished": "2026-04-29",
      "author": { "@id": "https://www.kleinezeitung.at/autor/1/peter-altmann" }
    }
  ]
}
```

This is embedded in the `<head>` of each article page as a `<script type="application/ld+json">` block.

---

## Project Structure

```
author-rich-snippets-EEAT-/
├── pipeline.py              # Main CLI orchestrator
├── scraper/
│   ├── auth.py              # Playwright login + session cookie handling
│   ├── discover.py          # Author listing page parser
│   ├── articles.py          # Article scraper (2025–2026, max 15)
│   ├── enrich.py            # Wikipedia + social link enrichment
│   ├── generate.py          # Claude API bio generation
│   ├── render.py            # Schema.org JSON-LD renderer
│   ├── schema.py            # Author JSON schema + factory
│   └── state.py             # SQLite state machine
├── review/
│   ├── export.py            # Exports author_review.xlsx for editorial review
│   └── importer.py          # Imports approved edits back into JSON + richsnippets
├── data/authors/            # Per-author JSON files (gitignored)
├── richsnippet/             # Per-author JSON-LD files (gitignored)
├── tests/                   # pytest test suite
├── .env.example             # Environment variable template
└── requirements.txt
```

---

## Adapting for Another News Organisation

The pipeline was built for Kleine Zeitung but the architecture is generic. To adapt it:

1. **Auth** (`scraper/auth.py`) — replace the Piano/TinyPass login flow with your site's auth
2. **Discover** (`scraper/discover.py`) — update the CSS selectors for your author listing pages
3. **Articles** (`scraper/articles.py`) — update selectors for your article page structure
4. **Render** (`scraper/render.py`) — update the `_PUBLISHER` block with your organisation's details
5. **Config** (`.env`) — update `KLZ_BASE_URL` and `KLZ_LOGIN_URL` with your domain

**Language:** The bio generation prompt in `scraper/generate.py` produces bios in **German** and is tuned to the tone and style of Austrian print journalism. If you are adapting this for a non-German-speaking outlet, you will need to rewrite the prompt (look for the `build_prompt()` function). The rest of the pipeline — scraping, enrichment, JSON-LD output, review workflow — is language-independent.

---

## Feasibility for Other News Websites

**What transfers immediately (no changes needed):**
- The state machine, pipeline orchestrator, and incremental re-run logic
- The bio generation stage (just update the prompt language)
- The Schema.org JSON-LD output format
- The entire editorial review workflow (Excel export → Google Sheets → import)

**What needs CSS selector work (1–2 days per site):**
- `scraper/discover.py` — finding author profile URLs depends on how your site structures its author listing pages. You need to inspect the HTML and update the selectors.
- `scraper/articles.py` — article metadata (title, date, section) is extracted from HTML attributes specific to the Kleine Zeitung CMS (CUE by Stibo). Other CMSes will have different markup.

**What may require significant effort:**

| Requirement | Notes |
|---|---|
| Dedicated author pages | The pipeline assumes each author has a stable `/autor/{id}/{slug}` profile URL. Sites that don't have author pages (byline-only) need a different discovery approach. |
| Login-protected content | The scraper handles Piano/TinyPass (common in DACH media). Other paywalls (Piano.io, Plenigo, Leaky Paywall) will need their own auth flow in `scraper/auth.py`. |
| JavaScript-heavy pages | Playwright handles JS rendering, so most modern sites work. However, sites with aggressive bot detection (Cloudflare, DataDome) may block headless browsers. |
| Article date format | The 2025–2026 filter in `scraper/articles.py` assumes ISO date strings. Other date formats need a parser update. |

**Realistic estimate:** For a standard DACH news site with author pages and Piano authentication, adapting the scraper takes roughly **one day of HTML inspection + selector updates**. For a site with a different CMS or no dedicated author pages, budget a full week.

---

## Tech Stack

| Component | Library |
|---|---|
| Browser automation | [Playwright](https://playwright.dev/python/) |
| HTTP client | [httpx](https://www.python-httpx.org/) |
| HTML parsing | [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) + lxml |
| Bio generation | [Anthropic Claude API](https://docs.anthropic.com/) (`claude-sonnet-4-6`) |
| Excel output | [openpyxl](https://openpyxl.readthedocs.io/) |
| State tracking | SQLite (stdlib) |
| Tests | [pytest](https://pytest.org/) |

---

## Running Tests

```bash
pytest tests/ -v
```

> Note: `test_articles.py` and `test_discover.py` have 11 known failures due to live CSS selector changes on the target site — these are pre-existing and unrelated to the core pipeline logic.

---

## License

MIT
