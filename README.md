# AI Trader Agent

This repository contains a paper trading dashboard built with a Python FastAPI backend and a Next.js frontend.

## What’s included

- `backend/`: FastAPI backend, paper execution engine, agent loop, and test suite.
- `frontend/`: Next.js dashboard styled with Tailwind CSS.
- `vercel.json`: Vercel deployment configuration for the frontend.

## Deploying the frontend to Vercel

### Prerequisites

- Install Node.js and npm on your machine.
- Install the Vercel CLI:
  ```bash
  npm install -g vercel
  ```
- Ensure this repository is tracked by Git and pushed to GitHub if you want to deploy from there.

### Deploy from this repository

1. Open a terminal at the repo root:
   ```bash
   cd "/Users/gourabmalakar/Built applications/AI Trader agent"
   ```
2. Deploy the frontend to Vercel:
   ```bash
   vercel
   ```
3. Follow the CLI prompts. The `vercel.json` file is already configured to deploy `frontend/` as the Next.js app.

### If you want a production deploy directly:

```bash
vercel --prod
```

## Local frontend preview

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```
2. Run the development server:
   ```bash
   npm run dev
   ```
3. Open the app in your browser at `http://localhost:3000`.

## Backend note

The backend is a Python FastAPI service in `backend/`. It is not automatically deployed by the current Vercel configuration. If you want the dashboard to use live backend data instead of fallback/mock data, deploy the backend separately and set the environment variable `NEXT_PUBLIC_API_URL` in Vercel to your backend URL.

## Recommended Vercel settings

- Project root: repo root
- Framework preset: `Next.js`
- Build command: `cd frontend && npm install && npm run build`
- Output directory: `frontend/.next`
- Environment variable (optional):
  - `NEXT_PUBLIC_API_URL` = `https://your-backend.example.com`
