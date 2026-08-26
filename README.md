# AI Trader Agent

A public, judgeable paper-trading scoreboard: **₹1 crore deployed across the NIFTY 50 by an
autonomous multi-factor trading agent, benchmarked against NIFTY itself**, with every trade
logged with its rationale, an independent compliance audit re-checking every fill, and a
CIO-style research desk — all viewable by anyone, no login required.

> This is a **paper-trading simulation**. No real money, brokerage account, or live order ever
> exists. It exists to demonstrate an autonomous, LLM-assisted trading system end-to-end, publicly
> and transparently.

## What it actually does

Every ~15 minutes during NSE trading hours (09:15–15:30 IST, weekdays), the agent:

1. Scores the full **NIFTY 50** on 20-day momentum, relative strength vs. the index, and RSI.
2. Shortlists the strongest signals and asks an LLM (**Gemini**, with **Claude** as a capped
   fallback) to review them against public fundamentals and recent news, and write the rationale
   for each call — falling back to deterministic quant scoring alone if both providers are
   unavailable or rate-limited, so the agent never goes silent.
3. Applies a **value/quality tilt** (PE, margins, debt/equity) and a **news-risk overlay** to every
   buy's sizing — this runs regardless of which engine made the call, so even a quant-only cycle
   is fundamentals- and news-aware, not purely price-technical.
4. Scales overall exposure to the current **market regime** (risk-on/neutral/risk-off) instead of
   always trying to deploy near its cap.
5. Enforces a hard **stop-loss (-8%)** and **profit-taking trim (+20%)** on every open position,
   overriding any upstream signal — capital preservation before conviction.
6. Executes through a **risk-managed paper execution engine** (position caps, cash buffer,
   trading-window enforcement) and logs every fill *and every rejection* with its reasoning.
7. Gets independently re-audited by a **Governance Officer** — a detective control, separate from
   the preventive risk engine, that re-checks every fill after the fact against the fund's own
   stated rules and reports findings publicly, not just a self-report from the trading logic.

Daily trade-summary emails, a weekly market outlook, and a monthly portfolio review are generated
and sent automatically; a failure anywhere in the pipeline triggers an alert email independent of
whether the backend itself is reachable.

## Live

- **Dashboard:** deployed on Vercel (frontend) + Render (backend) — see [Deploying](#deploying) for
  how to stand up your own copy.
- **API:** `GET /health`, `GET /api/dashboard`, `GET /api/trades` (paginated trade history +
  Excel export) are all public and unauthenticated.

## Architecture

```mermaid
flowchart TB
    subgraph Scheduling["GitHub Actions (cron)"]
        TT["trading-tick.yml<br/>every 15 min, market hours"]
        DC["daily-close.yml<br/>~15:35 IST"]
        WO["weekly-outlook.yml<br/>Fridays"]
        MR["monthly-review.yml<br/>last trading day"]
        KA["keepalive.yml<br/>every 10 min"]
    end

    subgraph Backend["FastAPI backend (Render)"]
        API["/api/cron/run<br/>/api/notify/*<br/>/api/dashboard<br/>/api/trades"]
        Loop["PortfolioAgentLoop"]
        Quant["Quant scoring<br/>momentum · RSI · relative strength"]
        Decision["Decision engine<br/>Gemini → Claude → quant-only"]
        Tilt["Fundamentals/news tilt +<br/>stop-loss / take-profit"]
        Risk["RiskManager<br/>(preventive)"]
        Exec["PaperExecutionEngine"]
        Gov["GovernanceOfficer<br/>(detective audit)"]
        Ledger["PortfolioLedger"]
    end

    subgraph Data["Data sources"]
        Yahoo["Yahoo Finance<br/>prices + fundamentals"]
        FMP["Financial Modeling Prep<br/>fundamentals fallback"]
    end

    subgraph External["External services"]
        Neon[("Neon Postgres<br/>persistent state")]
        GeminiAPI["Google Gemini API"]
        ClaudeAPI["Anthropic Claude API"]
        Resend["Resend<br/>email"]
    end

    Frontend["Next.js dashboard (Vercel)<br/>public, no login"]

    TT --> API
    DC --> API
    WO --> API
    MR --> API
    KA --> API

    API --> Loop
    Loop --> Quant --> Decision
    Decision <--> GeminiAPI
    Decision <--> ClaudeAPI
    Decision --> Tilt --> Risk --> Exec --> Ledger
    Loop --> Gov
    Quant <--> Yahoo
    Tilt <--> Yahoo
    Tilt <--> FMP
    Loop <--> Neon
    API --> Resend

    Frontend -->|"GET /api/dashboard, /api/trades"| API
```

## Key design decisions (and why)

| Decision | Why |
|---|---|
| Quant scoring is always free/deterministic; the LLM is a *review* layer on top | Keeps the agent trading even when Gemini's free tier is exhausted — the dashboard tags every decision with which engine produced it (`gemini` / `claude` / `quant_only`), so nothing is hidden. |
| Fundamentals/news tilt and stop-loss/take-profit run *after* the LLM, unconditionally | Risk discipline should never depend on whether an LLM call happened to succeed that cycle. |
| Governance is a separate audit pass, not part of the trading logic | A self-report from the code that decided the trades proves nothing; an independent re-check of the same data does. |
| State persists in Postgres, not in-memory | A free-tier backend redeploys often; in-memory state would silently reset the "continuous track record" this whole project is about. |
| LLM calls are capped and skip when nothing material changed | Google's free tier is ~20 requests/day for the model in use — this is a real, hard constraint, not a style choice. |

## Known limitations

Being transparent about what's genuinely unresolved, not just what works:

- **Public fundamentals (PE, margins, debt/equity) can show partial data.** Yahoo Finance's
  `.info` endpoint appears to be rate-limited or blocked for some cloud-hosting IP ranges
  (confirmed: identical code returns full data from a residential IP, empty from a Render
  deployment). A [Financial Modeling Prep](https://financialmodelingprep.com) fallback is wired
  in (`FMP_API_KEY`) but needs a live key to fully verify.
- **Gemini's free tier is genuinely small** (order of 20 requests/day for the model in use). The
  agent is designed to ration and fall back gracefully, but this means many cycles run on
  deterministic quant scoring alone rather than LLM review, especially early in a trading day.
- **This is a long-only equity strategy.** There is no options hedging, shorting, or pairs
  trading — the "multi-strategy" design here means multiple *factors* (momentum, value/quality,
  news risk, regime exposure, stop-loss discipline) combined into one long-only book, not multiple
  independent trading strategies running in parallel.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python 3.11, FastAPI |
| Frontend | Next.js 16 (App Router), Tailwind CSS v4, Recharts |
| Database | Postgres (Neon) |
| LLMs | Google Gemini (primary), Anthropic Claude (fallback) |
| Market data | Yahoo Finance (`yfinance`), Financial Modeling Prep (fundamentals fallback) |
| Email | Resend |
| Hosting | Render (backend), Vercel (frontend) |
| Scheduling | GitHub Actions (cron) |
| Excel export | `openpyxl` |

## Repository structure

```
backend/
  app/
    agents/          # quant scoring, market-regime classification, the main PortfolioAgentLoop
    llm/              # Gemini/Claude decision engine, budget rationing, chat fallback
    governance/       # independent post-hoc compliance audit
    risk/             # preventive order-level risk checks
    execution/        # paper fill engine
    portfolio/        # ledger (positions, cash, realized/unrealized P&L)
    data/             # NIFTY 50 universe, fundamentals providers
    notify/           # Resend email (daily/weekly/monthly, failure alerts)
    export/           # Excel trade-log export
  tests/              # pytest suite (63+ tests)
frontend/
  src/
    app/page.tsx      # the dashboard (server component, force-dynamic)
    components/       # PortfolioHero, PerformanceChart, TradeLog, GovernancePanel, ...
.github/workflows/    # CI + the scheduled trading/notification/keepalive jobs
```

## Deploying

### 1. Database — Neon Postgres

Create a free project at [neon.tech](https://neon.tech) and copy its connection string
(`postgresql://user:password@host/dbname?sslmode=require`). Render's own free Postgres
auto-deletes after 30 days, which would wipe trade history — Neon's free tier is persistent.

### 2. Backend — Render

Import this repo into [render.com](https://render.com) as a Web Service; it picks up
`backend/render.yaml` automatically. Set these environment variables:

| Variable | Required | Source |
|---|---|---|
| `DATABASE_URL` | Yes | Neon connection string (step 1) |
| `GEMINI_API_KEY` | Yes | [Google AI Studio](https://aistudio.google.com/apikey) |
| `ANTHROPIC_API_KEY` | Yes | [console.anthropic.com](https://console.anthropic.com) |
| `CRON_SECRET` | Yes | Any random string; shared with GitHub Actions |
| `RESEND_API_KEY` | Yes | [resend.com](https://resend.com) |
| `ALERT_EMAIL_TO` | Yes | Where daily summaries / failure alerts go |
| `FMP_API_KEY` | Optional | [financialmodelingprep.com](https://financialmodelingprep.com) — fundamentals fallback |

Render's free tier spins the service down after ~15 min idle — `keepalive.yml` pings `/health`
every 10 minutes to keep it warm and doubles as an uptime alert.

### 3. Frontend — Vercel

Import the repo (root `vercel.json` builds `frontend/`). Set `NEXT_PUBLIC_API_URL` to the live
Render URL. In **Settings → Deployment Protection**, make sure Production is publicly accessible
— otherwise logged-out visitors hit a login wall instead of the dashboard.

### 4. Autonomy — GitHub Actions secrets

Repo → **Settings → Secrets and variables → Actions**:

- `BACKEND_URL` — the live Render URL
- `CRON_SECRET` — must match the backend's
- `RESEND_API_KEY`, `ALERT_EMAIL_TO` — used as a backstop alert path if the backend is unreachable

| Workflow | Cadence | Purpose |
|---|---|---|
| `ci.yml` | every push/PR to `main` | backend pytest + frontend build |
| `trading-tick.yml` | every 15 min, 09:15–15:30 IST, weekdays | runs a trading cycle |
| `daily-close.yml` | ~15:35 IST, weekdays | trade summary email |
| `weekly-outlook.yml` | Fridays ~15:35 IST | research note + email |
| `monthly-review.yml` | last trading day of month, close | portfolio review + email |
| `keepalive.yml` | every 10 min | keeps Render warm, uptime alert |

## Local development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.server:app --reload --port 8000

# Frontend (point it at your local backend)
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > frontend/.env.local
cd frontend
npm install
npm run dev
```

Run the backend test suite: `cd backend && python -m pytest -q`

## Token/cost controls

- Gemini is called at most once per trading cycle (not once per symbol) and only for a shortlist
  of the strongest quant signals — never the full 50-stock universe.
- If nothing material changed since the last cycle *and* the last review was a real LLM call
  (not a quant-only fallback), the LLM call is skipped and the prior decision reused.
- 429 (quota exceeded) is never retried — retrying just burns more of the same scarce daily
  budget. 503 (transient overload) gets a short-backoff retry.
- Claude is a hard-capped fallback (default 3 trading calls/day) used only when Gemini errors or
  is rate-limited; weekly/monthly research notes have their own small, separate budget.
- The chat box is intentionally scoped out of LLM usage entirely (cap 0 by default) so trading
  decisions and research get the whole of Gemini's limited free-tier daily quota.
- If both providers are unavailable/capped, the deterministic quant engine still runs and trades
  are clearly tagged `quant_only` in the dashboard — the agent never fabricates a review it didn't
  actually get.

## License

[MIT](LICENSE)
