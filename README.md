# PokéBargain

**AI-powered Pokémon card bargain finder for eBay UK**

Built by **Muhammad Muazzain** ([muhammadmuazzain07@gmail.com](mailto:muhammadmuazzain07@gmail.com))

PokéBargain continuously scans eBay UK with **broad** Pokémon search terms, identifies the exact card being sold (even when titles are misspelled, vague, or generic), pulls market prices from the Pokémon TCG API, and ranks listings by a **Hidden Opportunity Score** — so you surface undervalued singles that ordinary keyword searches miss.

This is an MVP designed for Railway deployment, with a clear path to a full discovery platform.

---

## Why this exists

Price comparison alone is not enough.

The valuable listings are the ones **other buyers overlook**:

| Listing title | What it actually is |
| --- | --- |
| `Charzard holo pokemon card` | Base Set Charizard |
| `Obsidan Flames art rare` | Obsidian Flames Charizard ex |
| `pokemon rare card` + photo | Identified via OpenAI Vision |

PokéBargain is built around that discovery problem.

---

## Features (MVP)

1. **Broad listing discovery** — eBay Browse API on marketplace `EBAY_GB`, Buy It Now singles, configurable search terms (including common misspellings).
2. **Single-card filtering** — drops obvious accessories, sealed product, and bulk lots.
3. **Fuzzy text matching** — RapidFuzz against the Pokémon TCG database with spelling correction and confidence scores.
4. **OpenAI Vision (cost-aware)** — only runs when fuzzy confidence is below a configurable threshold (default 90%).
5. **Market pricing** — Pokémon TCG API (TCGplayer / Cardmarket where available); discount £ / %, potential profit.
6. **Hidden Opportunity Score (0–100)** — misspellings, poor titles, missing card numbers, vision upgrades, price gap, ID confidence.
7. **Dashboard** — card image, name, eBay price, market value, score, profit, discount %, eBay link, found time; sort by score / discount / profit / newest.
8. **Background scanner** — APScheduler interval scans with duplicate suppression by eBay item ID.
9. **PostgreSQL-ready** — SQLAlchemy models for listings, scores, and scan history (SQLite for local demos).
10. **Secrets via env** — no hardcoded keys; Docker + Railway ready.

---

## Architecture

```
eBay Browse API  ──►  Filter singles  ──►  RapidFuzz match  ──┬──►  TCG market price  ──►  Opportunity Score  ──►  Dashboard
                                              │                │
                                   confidence < threshold?     │
                                              │                │
                                              └── OpenAI Vision ┘
```

| Layer | Tech |
| --- | --- |
| API / UI | Python 3.11+, FastAPI, Jinja2 |
| Matching | RapidFuzz |
| Vision | OpenAI Vision (optional, gated) |
| Data | SQLAlchemy → PostgreSQL (Railway) or SQLite |
| Jobs | APScheduler background scanner |
| Deploy | Docker, Railway |

---

## Quick start

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
# or: pip install -e .

cp .env.example .env
# fill in eBay Client ID/Secret, Pokémon TCG API key, OpenAI key

pokebargain init-db
pokebargain seed-demo          # optional sample bargains for UI walkthrough
pokebargain serve              # http://127.0.0.1:8000
```

With live credentials:

```bash
pokebargain scan               # one scan cycle
pokebargain serve              # dashboard + background scans (POKEBARGAIN_AUTO_SCAN=true)
```

---

## Configuration

All settings use the `POKEBARGAIN_` prefix (see `.env.example`).

| Variable | Purpose |
| --- | --- |
| `POKEBARGAIN_EBAY_CLIENT_ID` / `_SECRET` | eBay application credentials |
| `POKEBARGAIN_EBAY_MARKETPLACE_ID` | Default `EBAY_GB` |
| `POKEBARGAIN_POKEMON_TCG_API_KEY` | pokemontcg.io key |
| `POKEBARGAIN_OPENAI_API_KEY` | Vision fallback |
| `POKEBARGAIN_FUZZY_CONFIDENCE_THRESHOLD` | Default `90` |
| `POKEBARGAIN_DATABASE_URL` | SQLite or `postgresql+psycopg://...` |
| `POKEBARGAIN_SCAN_INTERVAL_SECONDS` | Background scan interval |
| `POKEBARGAIN_MIN_OPPORTUNITY_SCORE` | Dashboard filter (default `75`) |

---

## Hidden Opportunity Score

| Score | Meaning |
| --- | --- |
| 100 | Extremely likely hidden bargain |
| 90+ | Very strong opportunity |
| 75+ | Worth reviewing |
| &lt; 75 | Low priority (hidden from default dashboard) |

Signals include misspelled names/sets, generic/vague titles, missing card numbers, vision identifying a better card than the title, asking-price vs market gap, and match confidence.

---

## Deployment (Railway)

1. Create a Railway project and add a **PostgreSQL** plugin.
2. Set environment variables from `.env.example` (map `DATABASE_URL` into `POKEBARGAIN_DATABASE_URL` if needed).
3. Deploy from this repo (Dockerfile + `railway.toml` included).
4. Health check: `GET /health`.

```bash
docker build -t pokebargain .
docker run --env-file .env -p 8000:8000 pokebargain
```

---

## Project layout

```
src/pokebargain/
  ebay/          # OAuth app token + Browse search
  tcg/           # Pokémon TCG API client
  matching/      # single-card filter + RapidFuzz
  vision/        # OpenAI Vision (gated)
  scoring/       # Hidden Opportunity Score
  pipeline/      # scan orchestration
  scanner/       # background scheduler
  db/            # SQLAlchemy models + repos
  web/           # FastAPI dashboard + JSON API
```

---

## API

- `GET /` — HTML dashboard  
- `GET /api/opportunities?sort=score|discount|profit|newest` — JSON  
- `POST /scan` — trigger a scan  
- `GET /health` — liveness  

---

## Suggested MVP timeline

| Phase | Scope | Estimate |
| --- | --- | --- |
| 1 | eBay UK broad scan + DB + filters | ~2–3 days |
| 2 | Fuzzy match + TCG pricing + opportunity score | ~3–4 days |
| 3 | Vision fallback + dashboard + background job | ~2–3 days |
| 4 | Docker / Railway hardening + polish | ~1–2 days |

**MVP total: ~1.5–2 weeks** depending on API access and eBay app approval.

---

## Architecture notes / next improvements

- Cache TCG catalogue in Postgres instead of process memory for faster cold starts.
- Add FX feed for cleaner USD/EUR → GBP conversion.
- Persist rejected listings with reasons for filter tuning.
- Optional Marketplace Insights (sold comps) when eBay grants access.
- Later phases: multi-card lots, sealed product, alerts / Discord, browser extension.

---

## Author

**Muhammad Muazzain**  
Email: [muhammadmuazzain07@gmail.com](mailto:muhammadmuazzain07@gmail.com)  
GitHub: [MuhammadMuazzain](https://github.com/MuhammadMuazzain)

Stack experience demonstrated in this repo: Python, FastAPI, REST APIs, PostgreSQL/SQLAlchemy, Docker, eBay Browse API, Pokémon TCG API, OpenAI Vision, RapidFuzz, Railway-oriented deployment.

---

## License

MIT © 2026 Muhammad Muazzain
