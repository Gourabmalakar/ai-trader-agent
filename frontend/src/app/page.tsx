import { getDashboardData } from '@/lib/api';
import { PortfolioHero } from '@/components/PortfolioHero';
import { PerformanceChart } from '@/components/PerformanceChart';
import { HoldingsTable } from '@/components/HoldingsTable';
import { TradeLog } from '@/components/TradeLog';
import { EventLog } from '@/components/EventLog';
import { SchedulerPanel } from '@/components/SchedulerPanel';
import { MarketIntelligence } from '@/components/MarketIntelligence';
import { ResearchNotes } from '@/components/ResearchNotes';
import { CapitalAllocation } from '@/components/CapitalAllocation';
import { SectorAllocation } from '@/components/SectorAllocation';
import { GovernancePanel } from '@/components/GovernancePanel';
import { DashboardRefresh } from '@/components/DashboardRefresh';

// Without this, Next.js would prerender "/" as static HTML at build time (as it does by
// default whenever nothing marks a route dynamic) and every visitor — plus every 30s
// DashboardRefresh poll — would keep seeing that frozen build-time snapshot instead of the
// live backend state. This is the single most important line for "why isn't the dashboard
// updating": it forces this route to always render fresh on the server per request.
export const dynamic = 'force-dynamic';
export const revalidate = 0;

// Vercel's serverless function has its own execution timeout (as short as ~10s by default on
// some plans). Render's free backend can take 20-50s to wake from a cold start, so without this,
// Vercel could give up and this page would show the "offline" fallback for a backend that was
// actually fine, just still booting — a second refresh moments later would then work. 60s is the
// Hobby-plan ceiling; raise it if this project is on Pro or higher.
export const maxDuration = 60;

function formatCompactNumber(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A';
  return new Intl.NumberFormat('en-IN', { notation: 'compact', maximumFractionDigits: 1 }).format(value);
}

export default async function Home() {
  const data = await getDashboardData();
  const latestHeadlineCount = data.publicSignals?.headlines.length ?? data.marketIntelligence?.headlineCount ?? 0;
  const freshness = data.scheduler.lastMarketDataAt ? new Date(data.scheduler.lastMarketDataAt).toLocaleString('en-IN') : 'refresh pending';

  return (
    <main className="min-h-screen px-4 py-6 text-slate-100 lg:px-8">
      <DashboardRefresh />
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <header className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-[linear-gradient(135deg,rgba(15,23,42,0.95),rgba(2,6,23,0.92))] p-6 shadow-[0_40px_120px_rgba(0,0,0,0.32)] sm:p-8">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(34,197,94,0.18),transparent_30%),radial-gradient(circle_at_bottom_left,rgba(245,158,11,0.16),transparent_28%)]" />
          <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <div className="flex flex-wrap items-center gap-3">
                <span className={`rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.28em] ${data.isFallback ? 'border-amber-400/30 bg-amber-400/10 text-amber-200' : 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200'}`}>
                  {data.isFallback ? 'Offline mode' : 'Public live paper dashboard'}
                </span>
                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.28em] text-slate-300">
                  {latestHeadlineCount} public headlines
                </span>
                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.28em] text-slate-300">
                  Last market data: {freshness}
                </span>
              </div>
              <h1 className="mt-5 text-4xl font-semibold tracking-tight text-slate-50 sm:text-5xl lg:text-6xl">
                AI trader vs NIFTY
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
                This public scoreboard answers one question fast: if you put 1 crore into NIFTY on the inception date, how much would it be worth today, and how did the AI agent compare after every logged trade and public signal?
              </p>
            </div>

            <div className="grid gap-3 rounded-3xl border border-white/10 bg-black/20 p-4 text-sm text-slate-300 backdrop-blur">
              <div className="flex justify-between gap-8">
                <span>Data source</span>
                <span className="font-medium text-slate-100">{data.dataStatus?.source ?? 'Backend'}</span>
              </div>
              <div className="flex justify-between gap-8">
                <span>State</span>
                <span className="font-medium text-slate-100">{data.scheduler.status.replace(/_/g, ' ')}</span>
              </div>
              <div className="flex justify-between gap-8">
                <span>Open positions</span>
                <span className="font-medium text-slate-100">{data.portfolio.openPositions ?? 0} / {data.portfolio.universeSize ?? 50} tracked</span>
              </div>
              <div className="flex justify-between gap-8">
                <span>Trades logged</span>
                <span className="font-medium text-slate-100">{data.portfolio.tradeCount ?? 0}</span>
              </div>
            </div>
          </div>
        </header>

        {data.isFallback && (
          <div className="rounded-2xl border border-amber-400/20 bg-amber-400/10 px-5 py-4 text-sm text-amber-100">
            The backend was not reachable, so the dashboard is showing the safe offline state. Once the API is connected, the page will update without changing the layout.
          </div>
        )}

        <PortfolioHero portfolio={data.portfolio} comparison={data.comparison} />

        <section className="grid gap-6 xl:grid-cols-[1.95fr_1fr]">
          <PerformanceChart data={data.performance} />
          <SchedulerPanel scheduler={data.scheduler} />
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.3fr_1fr]">
          <CapitalAllocation allocation={data.capitalAllocation} />
          <SectorAllocation allocation={data.sectorAllocation} />
        </section>

        <HoldingsTable holdings={data.holdings} />

        <section className="grid gap-6 xl:grid-cols-[1.3fr_0.9fr]">
          <TradeLog />
          <MarketIntelligence items={data.marketIntelligence?.items ?? []} />
        </section>

        <GovernancePanel governance={data.governance} />

        <ResearchNotes research={data.research} />

        <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
          <div className="rounded-[1.75rem] border border-white/8 bg-white/[0.04] p-5">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-slate-100">Public fundamentals</h2>
              <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] uppercase tracking-[0.3em] text-slate-400">Balance sheet and cashflow</span>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {(data.publicSignals?.fundamentals ?? []).map((item) => {
                const fields: Array<[string, string | null]> = [
                  ['PE', item.trailingPE != null ? item.trailingPE.toFixed(1) : null],
                  ['Fwd PE', item.forwardPE != null ? item.forwardPE.toFixed(1) : null],
                  ['PB', item.priceToBook != null ? item.priceToBook.toFixed(1) : null],
                  ['Debt/Equity', item.debtToEquity != null ? item.debtToEquity.toFixed(0) : null],
                  ['Margins', item.profitMargins != null ? `${(item.profitMargins * 100).toFixed(1)}%` : null],
                  ['Rev growth', item.revenueGrowth != null ? `${(item.revenueGrowth * 100).toFixed(1)}%` : null],
                  ['FCF', item.freeCashflow != null ? formatCompactNumber(item.freeCashflow) : null],
                  ['Earnings', item.earningsGrowth != null ? `${(item.earningsGrowth * 100).toFixed(1)}%` : null],
                ];
                const available = fields.filter(([, value]) => value !== null);
                return (
                  <div key={item.symbol} className="rounded-2xl border border-white/8 bg-black/20 p-4">
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <p className="font-semibold text-slate-100">{item.name}</p>
                        <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{item.symbol}</p>
                      </div>
                      <span className="text-sm text-slate-300">{item.marketCap != null ? formatCompactNumber(item.marketCap) : 'N/A'}</span>
                    </div>
                    {available.length > 0 ? (
                      <div className="mt-4 grid grid-cols-2 gap-2 text-sm text-slate-300">
                        {available.map(([label, value]) => (
                          <div key={label}>{label}: {value}</div>
                        ))}
                      </div>
                    ) : (
                      <p className="mt-4 text-xs text-slate-500">
                        Ratios temporarily unavailable from the data provider for this symbol — market cap still updates independently.
                      </p>
                    )}
                  </div>
                );
              })}
              {!(data.publicSignals?.fundamentals?.length) && (
                <div className="rounded-2xl border border-white/8 bg-black/20 p-4 text-sm text-slate-400 md:col-span-2">
                  No public fundamental snapshot is currently available.
                </div>
              )}
            </div>
          </div>

          <div className="rounded-[1.75rem] border border-white/8 bg-white/[0.04] p-5">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-slate-100">Strategy summary</h2>
              <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] uppercase tracking-[0.3em] text-slate-400">Transparent rules</span>
            </div>
            <p className="mt-4 text-sm leading-7 text-slate-300">{data.investmentThesis?.summary}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {(data.investmentThesis?.focus ?? []).map((item) => (
                <span key={item} className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-slate-300">
                  {item}
                </span>
              ))}
            </div>
            <div className="mt-6 rounded-2xl border border-white/8 bg-black/20 p-4">
              <h3 className="text-sm font-semibold text-slate-100">Risk profile</h3>
              <div className="mt-3 space-y-2 text-sm text-slate-300">
                <div className="flex justify-between"><span>Risk score</span><span>{data.riskProfile?.score ?? 0}/100</span></div>
                <div className="flex justify-between"><span>Cash buffer</span><span>{((data.riskProfile?.cashBuffer ?? 0) * 100).toFixed(1)}%</span></div>
                <div className="flex justify-between"><span>Max single stock</span><span>{data.riskProfile?.maxSingleStockWeight ?? 0}%</span></div>
                <div className="flex justify-between"><span>Max daily deployment</span><span>{data.riskProfile?.maxDailyDeployment ?? 0}%</span></div>
              </div>
              <div className="mt-3 rounded-xl border border-white/8 bg-black/30 p-3 text-xs leading-6 text-slate-400">
                {(data.riskProfile?.notes ?? []).join(' · ')}
              </div>
            </div>
          </div>
        </section>

        <EventLog />
      </div>

    </main>
  );
}
