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
    <section className="grid gap-4 lg:grid-cols-5">
      <MetricCard label="Portfolio Value" value={formatInr(portfolio.totalValue)} />
      <MetricCard label="Daily P&L" value={formatInr(portfolio.dailyPnl)} tone={portfolio.dailyPnl >= 0 ? 'profit' : 'loss'} />
      <MetricCard label="Total Return" value={formatPct(portfolio.totalReturn)} tone="profit" />
      <MetricCard label="NIFTY 100" value={formatPct(portfolio.benchmarkReturn)} />
      <MetricCard label="Alpha" value={formatPct(portfolio.alpha)} tone={portfolio.alpha >= 0 ? 'profit' : 'loss'} />
      <div className="rounded-2xl border border-amber/40 bg-amber/10 p-5 lg:col-span-5">
        <p className="text-xs uppercase tracking-[0.24em] text-amber">Market Regime</p>
        <p className="mt-2 text-xl font-semibold text-amber">{portfolio.marketRegime.replaceAll('_', ' ').toUpperCase()}</p>
      </div>
    </section>
  );
}
