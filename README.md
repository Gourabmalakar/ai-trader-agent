# AI Trader Agent

A public, judgeable paper-trading scoreboard: ₹1 Cr paper capital deployed across the NIFTY 50 by an
autonomous agent, benchmarked against NIFTY itself, with every trade logged with its LLM-authored
rationale. Gemini is the primary trading LLM (hourly during market hours); Claude is a capped fallback
used only when Gemini fails; deterministic quant scoring is the final safety net if both are unavailable.

## Architecture

- `backend/`: FastAPI service — market data, quant signals, the Gemini/Claude decision engine, paper
  execution/risk engine, Postgres-backed state, Resend email notifications.
- `frontend/`: Next.js dashboard (Tailwind v4), deployed on Vercel.
- Autonomous loop: GitHub Actions workflows in `.github/workflows/` call the backend on a schedule —
  there is no built-in scheduler process, the backend is stateless between calls and relies on Postgres
  + these external triggers.

The backend and frontend are **two separate deployments**. The frontend alone on Vercel cannot do
anything — it needs a live backend URL.

## Deploying the backend (Render + Neon Postgres)

1. Create a free Postgres database at [neon.tech](https://neon.tech) and copy its connection string
   (`DATABASE_URL`). Render's own free Postgres auto-deletes after 30 days, which would wipe trade
   history — Neon's free tier is persistent, so use it for `DATABASE_URL` regardless of where compute runs.
2. Create a new **Web Service** on [render.com](https://render.com) pointing at this repo; it will pick up
   `backend/render.yaml` automatically (root dir `backend`, `pip install -r requirements.txt`,
   `uvicorn app.server:app --host 0.0.0.0 --port $PORT`).
3. Set these environment variables on the Render service:
   - `DATABASE_URL` — the Neon connection string.
   - `GEMINI_API_KEY` — from [Google AI Studio](https://aistudio.google.com/apikey).
   - `ANTHROPIC_API_KEY` — from [console.anthropic.com](https://console.anthropic.com) (Claude fallback).
   - `CRON_SECRET` — any random string; shared with GitHub Actions to authorize the cron endpoints.
   - `RESEND_API_KEY` — from [resend.com](https://resend.com) (daily summary + failure alert emails).
   - `ALERT_EMAIL_TO` — already defaults to `greatgourab25@gmail.com` in `render.yaml`; change if needed.
4. Render's free tier spins the service down after ~15 min idle. The `keepalive.yml` GitHub Actions
   workflow pings `/health` every 10 minutes to keep it warm and doubles as an uptime alert.

## Deploying the frontend (Vercel)

1. Import this repo into Vercel; `vercel.json` builds `frontend/` as the Next.js app.
2. Set `NEXT_PUBLIC_API_URL` to the live Render backend URL (e.g. `https://ai-trader-agent-backend.onrender.com`).
3. **Deployment Protection**: in the Vercel project's Settings → Deployment Protection, make sure
   Production is publicly accessible — otherwise logged-out visitors get redirected to a Vercel login
   wall instead of the dashboard.

## Autonomous scheduling (GitHub Actions)

Set these repo secrets under Settings → Secrets and variables → Actions:

- `BACKEND_URL` — the live Render backend URL.
- `CRON_SECRET` — must match the backend's `CRON_SECRET`.
- `RESEND_API_KEY`, `ALERT_EMAIL_TO` — used as a backstop alert path if the backend itself is unreachable.

Workflows:
- `trading-tick.yml` — hourly, 09:15–15:30 IST, weekdays → `POST /api/cron/run`.
- `daily-close.yml` — ~15:35 IST, weekdays → `POST /api/notify/daily-summary` (trade summary email only).
- `weekly-outlook.yml` — Fridays ~15:35 IST → `POST /api/notify/weekly-outlook` (research note + email).
- `monthly-review.yml` — last trading day of each month ~15:40 IST → `POST /api/notify/monthly-review`.
- `keepalive.yml` — every 10 min → `GET /health`, keeps the free Render instance warm.

Each workflow also alerts directly via Resend on failure, independent of the backend, so a fully-down
backend still gets reported.

## Local development

Backend:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.server:app --reload --port 8000
```

Frontend (point it at your local backend via `frontend/.env.local`):
```bash
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > frontend/.env.local
cd frontend
npm install
npm run dev
```

Run the backend test suite:
```bash
cd backend && python -m pytest -q
```

## Token/cost controls

- Gemini is called at most once per trading cycle (not once per symbol) and only for a shortlist of the
  strongest quant signals — never the full 50-stock universe.
- If nothing material changed since the last cycle, the LLM call is skipped entirely and the prior
  decisions are reused.
- Claude is a hard-capped fallback (default 3 trading calls/day) used only when Gemini errors or is
  rate-limited; weekly/monthly research notes have their own small, separate budget.
- The chat box is intentionally scoped out of LLM usage entirely (cap 0 by default) so trading
  decisions and research get the whole of Gemini's limited free-tier daily quota; it still answers
  every question, just from the deterministic dashboard-state fallback.
- If both providers are unavailable/capped, the deterministic quant engine still runs and trades are
  clearly tagged `quant_only` in the dashboard — the agent never goes silent.
- Note: Gemini's free tier can be as low as 20 requests/day for a given model, which real hourly
  trading + weekly/monthly research can exhaust on its own. If you see persistent `quant_only`
  cycles, check Render's logs for `gemini call failed` entries — enabling billing on the Google AI
  Studio project raises this quota substantially and Gemini Flash models are inexpensive per call.
