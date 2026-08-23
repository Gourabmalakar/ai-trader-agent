import type { DashboardData } from '@/types/dashboard';

export function SchedulerPanel({ scheduler }: { scheduler: DashboardData['scheduler'] }) {
  const statusClass =
    scheduler.status === 'MARKET_OPEN'
      ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200'
      : scheduler.status === 'AFTER_HOURS'
      ? 'border-amber-400/30 bg-amber-400/10 text-amber-200'
      : 'border-white/10 bg-black/20 text-slate-300';

  return (
    <div className="rounded-[1.75rem] border border-white/8 bg-white/[0.04] p-5 shadow-[0_24px_80px_rgba(0,0,0,0.22)]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Agent runtime</h2>
          <p className="mt-2 text-sm text-slate-400">Freshness, market status, and when the next autonomous cycle is expected to run.</p>
        </div>
        <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${statusClass}`}>{scheduler.status.replace(/_/g, ' ')}</span>
      </div>
      <div className="mt-5 grid gap-3 text-sm text-slate-300">
        <div className="flex justify-between"><span>Trading Window</span><span>{scheduler.tradingWindow}</span></div>
        <div className="flex justify-between"><span>Last Run</span><span>{new Date(scheduler.lastRun).toLocaleString('en-IN')}</span></div>
        <div className="flex justify-between"><span>Next Market Open</span><span>{new Date(scheduler.nextMarketOpen).toLocaleString('en-IN')}</span></div>
        <div className="flex justify-between"><span>Last Agent Cycle</span><span>{scheduler.lastAgentCycle ? new Date(scheduler.lastAgentCycle).toLocaleString('en-IN') : 'Not run yet'}</span></div>
        <div className="flex justify-between"><span>Market Data</span><span>{scheduler.lastMarketDataAt ? new Date(scheduler.lastMarketDataAt).toLocaleString('en-IN') : 'Refreshing now'}</span></div>
        <div className="flex justify-between"><span>News refresh</span><span>{scheduler.lastNewsAt ? new Date(scheduler.lastNewsAt).toLocaleString('en-IN') : 'Refreshing now'}</span></div>
        <div className="flex justify-between"><span>Last review engine</span><span className="capitalize">{scheduler.lastEngineProvider?.replace('_', '-') ?? 'Not run yet'}</span></div>
      </div>
      {scheduler.lastEngineNote && (
        <p className="mt-4 rounded-xl border border-white/8 bg-black/20 p-3 text-xs leading-6 text-slate-400">{scheduler.lastEngineNote}</p>
      )}
    </div>
  );
}
