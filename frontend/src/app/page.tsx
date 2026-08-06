import { getDashboardData } from '@/lib/api';
import { PortfolioHero } from '@/components/PortfolioHero';
import { PerformanceChart } from '@/components/PerformanceChart';
import { HoldingsTable } from '@/components/HoldingsTable';
import { ReasoningFeed } from '@/components/ReasoningFeed';
import { SchedulerPanel } from '@/components/SchedulerPanel';
import { TradeBlotter } from '@/components/TradeBlotter';
import { MarketIntelligence } from '@/components/MarketIntelligence';
import { AgentChatModal } from '@/components/AgentChatModal';

export default async function Home() {
  const data = await getDashboardData();

  return (
    <main className="min-h-screen px-4 py-5 lg:px-8">
      {/* Top Ticker & System Header */}
      <header className="mb-6 flex flex-col gap-4 border-b border-grid pb-5 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <span className="flex h-2.5 w-2.5 rounded-full bg-profit animate-pulse"></span>
            <p className="text-xs uppercase tracking-[0.36em] text-profit font-semibold">
              AI Agentic Hedge Fund System · NSE India
            </p>
          </div>
          <h1 className="mt-1.5 text-3xl font-black tracking-tight text-slate-50 lg:text-5xl">
            Bloomberg Command Center
          </h1>
        </div>
        
        <div className="flex flex-wrap items-center gap-3">
          <div className="rounded-full border border-grid bg-panel/90 px-4 py-1.5 text-xs text-slate-300">
            Strategy: <span className="font-semibold text-profit">Delivery Swing Outperformance</span>
          </div>
          <div className="rounded-full border border-profit/40 bg-profit/10 px-4 py-1.5 text-xs font-semibold text-profit">
            Paper Capital: ₹1,00,00,000 (1 Crore)
          </div>
        </div>
      </header>

      {/* Portfolio Key Performance Metrics */}
      <PortfolioHero portfolio={data.portfolio} />

      {/* Performance Chart & Scheduler */}
      <section className="mt-6 grid gap-6 xl:grid-cols-[2.2fr_1fr]">
        <PerformanceChart data={data.performance} />
        <SchedulerPanel scheduler={data.scheduler} />
      </section>

      {/* Current Holdings & Executed Trade Blotter */}
      <section className="mt-6 grid gap-6 xl:grid-cols-[1.35fr_0.95fr]">
        <HoldingsTable holdings={data.holdings} />
        <TradeBlotter trades={data.trades} />
      </section>

      {/* Agent Reasoning Feed & News Intelligence */}
      <section className="mt-6 grid gap-6 xl:grid-cols-[1fr_1fr]">
        <ReasoningFeed decisions={data.decisions} />
        <MarketIntelligence items={data.marketIntelligence?.items ?? []} />
      </section>

      {/* Investment Thesis, Risk Profile & Market Outlook */}
      <section className="mt-6 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-2xl border border-grid bg-panel/80 p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-100">Investment Thesis</h2>
            <span className="rounded-full border border-profit/30 px-3 py-1 text-xs uppercase tracking-[0.24em] text-profit">
              Fund Manager Narrative
            </span>
          </div>
          <p className="mt-4 text-sm leading-7 text-slate-300">
            {data.investmentThesis?.summary ?? 'The portfolio prioritizes trend continuation in Nifty 50 leaders, strict position sizing caps, and tactical liquidity management.'}
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {(data.investmentThesis?.focus ?? []).map((item) => (
              <span key={item} className="rounded-full border border-grid bg-terminal/70 px-3 py-1 text-xs text-slate-300">
                {item}
              </span>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-grid bg-panel/80 p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-100">Risk Profile & Rules</h2>
            <span className="text-sm font-bold text-profit">{data.riskProfile?.score ?? 0}/100 Risk Score</span>
          </div>
          <div className="mt-4 space-y-3 text-sm text-slate-300">
            <div className="flex items-center justify-between">
              <span>Risk Posture</span>
              <span className="font-semibold text-slate-100">{data.riskProfile?.posture ?? 'Balanced Growth'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Cash Reserve Buffer</span>
              <span className="font-semibold text-profit">{((data.riskProfile?.cashBuffer ?? 0) * 100).toFixed(1)}%</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Max Single Stock Cap</span>
              <span>{data.riskProfile?.maxSingleStockWeight ?? 8}%</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Max Daily Deployment</span>
              <span>{data.riskProfile?.maxDailyDeployment ?? 25}%</span>
            </div>
            <div className="mt-3 rounded-xl border border-grid bg-terminal/70 p-3 text-xs leading-6 text-slate-400">
              {data.riskProfile?.notes?.join(' · ')}
            </div>
          </div>
        </div>
      </section>

      {/* Market Outlook Banner */}
      <section className="mt-6 rounded-2xl border border-grid bg-panel/80 p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-100">Market Outlook & Tactical Stance</h2>
            <p className="mt-2 text-sm leading-7 text-slate-300">{data.marketOutlook?.summary ?? 'Constructive but selective.'}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {(data.marketOutlook?.drivers ?? []).map((item) => (
              <span key={item} className="rounded-full border border-profit/20 bg-profit/10 px-3 py-1 text-xs uppercase tracking-[0.24em] text-profit">
                {item}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Interactive Agent Chat Floating Drawer */}
      <AgentChatModal />
    </main>
  );
}
