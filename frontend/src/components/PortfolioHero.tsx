import { formatInr, formatPct } from '@/lib/format';

export function MetricCard({ label, value, tone = 'neutral' }: { label: string; value: string | number; tone?: 'profit' | 'loss' | 'neutral' }) {
  const color = tone === 'profit' ? 'text-profit' : tone === 'loss' ? 'text-loss' : 'text-slate-100';
  return (
    <div className="rounded-2xl border border-grid bg-panel/80 p-5 shadow-glow backdrop-blur">
      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{label}</p>
      <p className={`mt-3 text-2xl font-semibold ${color}`}>{value}</p>
    </div>
  );
}

export function PortfolioHero({ portfolio }: { portfolio: { totalValue: number; dailyPnl: number; totalReturn: number; benchmarkReturn: number; alpha: number; marketRegime: string } }) {
  return (
    <section className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-3">
        <MetricCard label="AI Agent · Paper Return" value={formatPct(portfolio.totalReturn)} tone={portfolio.totalReturn >= 0 ? 'profit' : 'loss'} />
        <MetricCard label="NIFTY 50 · Benchmark Return" value={formatPct(portfolio.benchmarkReturn)} tone={portfolio.benchmarkReturn >= 0 ? 'profit' : 'loss'} />
        <MetricCard label="Alpha · Agent minus NIFTY" value={formatPct(portfolio.alpha)} tone={portfolio.alpha >= 0 ? 'profit' : 'loss'} />
      </div>
      <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr_1fr]">
        <MetricCard label="Paper Portfolio Value" value={formatInr(portfolio.totalValue)} />
        <MetricCard label="Session P&L" value={formatInr(portfolio.dailyPnl)} tone={portfolio.dailyPnl >= 0 ? 'profit' : 'loss'} />
        <div className="rounded-2xl border border-amber/40 bg-amber/10 p-5">
          <p className="text-xs uppercase tracking-[0.24em] text-amber">Market Regime</p>
          <p className="mt-2 text-xl font-semibold text-amber">{portfolio.marketRegime.replaceAll('_', ' ').toUpperCase()}</p>
        </div>
      </div>
    </section>
  );
}
