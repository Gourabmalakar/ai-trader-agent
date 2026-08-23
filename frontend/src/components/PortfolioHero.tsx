import { formatInr, formatPct } from '@/lib/format';

type HeroPortfolio = {
  totalValue: number;
  cash: number;
  investedValue: number;
  dailyPnl: number;
  totalReturn: number;
  benchmarkReturn: number;
  alpha: number;
  marketRegime: string;
  startingCapital?: number;
  inceptionDate?: string | null;
  tradeCount?: number;
  buyCount?: number;
  sellCount?: number;
  cashUtilizationPct?: number;
  deploymentPct?: number;
  openPositions?: number;
};

type Comparison = {
  inceptionDate: string | null;
  startingCapital: number;
  agentValue: number;
  agentReturnPct: number;
  agentProfit: number;
  niftyValue: number;
  niftyReturnPct: number;
  niftyProfit: number;
  alphaPct: number;
};

function MetricCard({ label, value, subtext, tone = 'neutral', size = 'md' }: { label: string; value: string | number; subtext?: string; tone?: 'profit' | 'loss' | 'neutral'; size?: 'md' | 'lg' }) {
  const color = tone === 'profit' ? 'text-emerald-300' : tone === 'loss' ? 'text-rose-300' : 'text-slate-100';
  return (
    <div className="rounded-[1.75rem] border border-white/8 bg-white/[0.04] p-5 shadow-[0_24px_80px_rgba(0,0,0,0.25)] backdrop-blur transition hover:border-white/15 hover:bg-white/[0.06]">
      <p className="text-[11px] font-medium uppercase tracking-[0.3em] text-slate-400">{label}</p>
      <p className={`mt-3 tabular-nums font-semibold tracking-tight ${size === 'lg' ? 'text-3xl sm:text-4xl' : 'text-2xl'} ${color}`}>{value}</p>
      {subtext && <p className="mt-2 text-sm leading-6 text-slate-400">{subtext}</p>}
    </div>
  );
}

function AlphaBar({ agentReturn, niftyReturn }: { agentReturn: number; niftyReturn: number }) {
  const max = Math.max(Math.abs(agentReturn), Math.abs(niftyReturn), 1);
  const agentWidth = Math.max(2, Math.min(100, (Math.abs(agentReturn) / max) * 100));
  const niftyWidth = Math.max(2, Math.min(100, (Math.abs(niftyReturn) / max) * 100));
  return (
    <div className="mt-5 space-y-2">
      <div className="flex items-center gap-3">
        <span className="w-14 text-[11px] uppercase tracking-[0.2em] text-emerald-300">Agent</span>
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/5">
          <div className={`h-full rounded-full ${agentReturn >= 0 ? 'bg-emerald-400' : 'bg-rose-400'}`} style={{ width: `${agentWidth}%` }} />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <span className="w-14 text-[11px] uppercase tracking-[0.2em] text-amber-300">NIFTY</span>
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/5">
          <div className={`h-full rounded-full ${niftyReturn >= 0 ? 'bg-amber-400' : 'bg-rose-400'}`} style={{ width: `${niftyWidth}%` }} />
        </div>
      </div>
    </div>
  );
}

export function PortfolioHero({ portfolio, comparison }: { portfolio: HeroPortfolio; comparison?: Comparison }) {
  const startingCapital = comparison?.startingCapital ?? portfolio.startingCapital ?? 0;
  const agentValue = comparison?.agentValue ?? portfolio.totalValue;
  const niftyValue = comparison?.niftyValue ?? portfolio.totalValue;

  return (
    <section className="grid gap-4">
      <div className="grid gap-4 xl:grid-cols-[1.35fr_0.85fr]">
        <div className="rounded-[2rem] border border-white/10 bg-[linear-gradient(135deg,rgba(15,23,42,0.94),rgba(2,6,23,0.92))] p-6 shadow-[0_30px_120px_rgba(0,0,0,0.35)]">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-[11px] uppercase tracking-[0.35em] text-emerald-300">Public paper trading scoreboard</p>
              <h2 className="mt-3 text-2xl font-semibold text-slate-50 sm:text-3xl">
                Rs 1 CR invested on {comparison?.inceptionDate ?? portfolio.inceptionDate ?? 'inception'}.
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-7 text-slate-400">
                The dashboard shows what Rs 1 CR would be worth in NIFTY versus what the AI agent made, with every executed trade and rationale logged below.
              </p>
            </div>
            <div className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-4 py-2 text-xs font-semibold text-emerald-200">
              {portfolio.marketRegime.replaceAll('_', ' ')}
            </div>
          </div>

          <div className="mt-6 grid gap-4 lg:grid-cols-3">
            <MetricCard
              size="lg"
              label="Agent value today"
              value={formatInr(agentValue)}
              subtext={`${formatPct(comparison?.agentReturnPct ?? portfolio.totalReturn)} since start`}
              tone={(comparison?.agentReturnPct ?? portfolio.totalReturn) >= 0 ? 'profit' : 'loss'}
            />
            <MetricCard
              size="lg"
              label="NIFTY value today"
              value={formatInr(niftyValue)}
              subtext={`${formatPct(comparison?.niftyReturnPct ?? portfolio.benchmarkReturn)} since start`}
              tone={(comparison?.niftyReturnPct ?? portfolio.benchmarkReturn) >= 0 ? 'profit' : 'loss'}
            />
            <MetricCard
              size="lg"
              label="Alpha"
              value={formatPct(comparison?.alphaPct ?? portfolio.alpha)}
              subtext={startingCapital ? `From a starting capital of ${formatInr(startingCapital)}` : 'Alpha versus benchmark'}
              tone={(comparison?.alphaPct ?? portfolio.alpha) >= 0 ? 'profit' : 'loss'}
            />
          </div>
          <AlphaBar agentReturn={comparison?.agentReturnPct ?? portfolio.totalReturn} niftyReturn={comparison?.niftyReturnPct ?? portfolio.benchmarkReturn} />
        </div>

        <div className="grid gap-4">
          <MetricCard label="Portfolio value" value={formatInr(portfolio.totalValue)} subtext={`${formatPct(portfolio.totalReturn)} total return`} tone={portfolio.totalReturn >= 0 ? 'profit' : 'loss'} />
          <MetricCard label="Cash / deployed" value={`${formatInr(portfolio.cash)} cash`} subtext={`${formatPct(portfolio.deploymentPct ?? 0)} deployed across ${portfolio.openPositions ?? 0} positions`} />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Daily P&L" value={formatInr(portfolio.dailyPnl)} tone={portfolio.dailyPnl >= 0 ? 'profit' : 'loss'} />
        <MetricCard label="Trades logged" value={String(portfolio.tradeCount ?? 0)} subtext={`${portfolio.buyCount ?? 0} buys · ${portfolio.sellCount ?? 0} sells`} />
        <MetricCard label="Cash utilization" value={`${(portfolio.cashUtilizationPct ?? 0).toFixed(1)}%`} />
        <MetricCard label="Benchmark return" value={formatPct(portfolio.benchmarkReturn)} tone={portfolio.benchmarkReturn >= 0 ? 'profit' : 'loss'} />
      </div>
    </section>
  );
}
