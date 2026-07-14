# PokéBargain

**eBay UK Pokémon TCG bargain scanner**

A production-oriented Python service that watches eBay UK for undervalued single-card listings — especially ones with weak titles, typos, or incomplete descriptions — and surfaces the best opportunities in a simple dashboard.

Originally built as a private client MVP; this public repo is a cleaned, documented version of that work.

**Author:** Muhammad Muazzain · [muhammadmuazzain07@gmail.com](mailto:muhammadmuazzain07@gmail.com)

---

## Background

A previous client needed automation that went beyond “compare price to market value.” Many profitable listings are overlooked because sellers write poor titles (`Charzard`, `Obsidan Flames`, `pokemon rare card`) or rely on the photo to tell the real story.

PokéBargain was built to:

- Run **broad** Pokémon searches on eBay UK (not only exact card names)
- Identify the card from title text, and fall back to vision only when needed
- Pull TCG market data and rank deals by how likely they are to be hidden bargains

---

## What it does

| Capability | Detail |
| --- | --- |
| Listing discovery | eBay Browse API (`EBAY_GB`), Buy It Now focus, configurable broad queries |
| Listing hygiene | Filters out accessories, sealed product, and bulk lots |
| Text matching | RapidFuzz against the Pokémon TCG catalogue; corrects common misspellings |
| Image fallback | OpenAI Vision when fuzzy confidence is below a threshold (default 90%) |
| Pricing | Pokémon TCG API (TCGplayer / Cardmarket fields where present) |
| Ranking | Hidden Opportunity Score from title quality, discount, and match confidence |
| UI | FastAPI dashboard — score, prices, profit estimate, eBay link, time found |
| Ops | Background scanner, duplicate suppression, env-based secrets, Docker / Railway |

---

## Pipeline

```
eBay Browse  →  single-card filter  →  RapidFuzz match  →  TCG market price  →  score  →  dashboard
                                       ↓ (low confidence)
                                 OpenAI Vision
```

**Stack:** Python 3.11+ · FastAPI · SQLAlchemy (PostgreSQL or SQLite) · RapidFuzz · OpenAI · APScheduler · Docker

---

## Quick start

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # add eBay, Pokémon TCG, and OpenAI credentials

pokebargain init-db
pokebargain seed-demo  # optional sample rows for a UI walkthrough
pokebargain serve      # http://127.0.0.1:8000
```

Live scan:

```bash
pokebargain scan
pokebargain serve      # background scans when POKEBARGAIN_AUTO_SCAN=true
```

---

## Configuration

Settings use the `POKEBARGAIN_` prefix. See `.env.example`.

| Variable | Purpose |
| --- | --- |
| `POKEBARGAIN_EBAY_CLIENT_ID` / `_SECRET` | eBay application credentials |
| `POKEBARGAIN_EBAY_MARKETPLACE_ID` | Defaults to `EBAY_GB` |
| `POKEBARGAIN_POKEMON_TCG_API_KEY` | [pokemontcg.io](https://pokemontcg.io/) API key |
| `POKEBARGAIN_OPENAI_API_KEY` | Vision fallback |
| `POKEBARGAIN_FUZZY_CONFIDENCE_THRESHOLD` | When to call Vision (default `90`) |
| `POKEBARGAIN_DATABASE_URL` | SQLite locally, or `postgresql+psycopg://...` |
| `POKEBARGAIN_SCAN_INTERVAL_SECONDS` | Background scan interval |
| `POKEBARGAIN_MIN_OPPORTUNITY_SCORE` | Dashboard cutoff (default `75`) |

---

## Opportunity scoring

Listings are ranked 0–100. Higher scores favour large price gaps plus signals that the listing is easy to miss (misspellings, generic titles, missing card numbers, vision agreeing on a better identity than the title). The default dashboard hides scores below 75.

Sortable views: highest score · biggest discount · highest potential profit · newest.

---

## Deploy

Dockerfile and `railway.toml` are included.

1. Provision PostgreSQL (e.g. Railway plugin).
2. Copy variables from `.env.example` into the host.
3. Deploy the container; health check at `GET /health`.

```bash
docker build -t pokebargain .
docker run --env-file .env -p 8000:8000 pokebargain
```

---

## Layout

```
src/pokebargain/
  ebay/       Browse API + app OAuth
  tcg/        Pokémon TCG API client
  matching/   filters + fuzzy matching
  vision/     OpenAI Vision (gated)
  scoring/    opportunity score
  pipeline/   scan orchestration
  scanner/    background scheduler
  db/         models + repositories
  web/        dashboard + JSON API
```

---

## HTTP surface

| Endpoint | Description |
| --- | --- |
| `GET /` | Dashboard |
| `GET /api/opportunities` | JSON (`sort=score\|discount\|profit\|newest`) |
| `POST /scan` | Trigger one scan |
| `GET /health` | Liveness |

---

## Possible extensions

Ideas that were out of scope for the original MVP, but fit naturally next:

- Persist the full TCG catalogue in Postgres (faster cold starts)
- Proper FX rates for USD/EUR → GBP
- Sold-comp pricing via eBay Marketplace Insights (where approved)
- Alerts (email / Discord), multi-card lots, sealed product lanes

---

## License

MIT © Muhammad Muazzain
