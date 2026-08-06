import type { DashboardData } from '@/types/dashboard';

export function SchedulerPanel({ scheduler }: { scheduler: DashboardData['scheduler'] }) {
  const statusClass =
    scheduler.status === 'MARKET_OPEN'
      ? 'border-profit/40 bg-profit/10 text-profit'
      : scheduler.status === 'AFTER_HOURS'
      ? 'border-amber/40 bg-amber/10 text-amber'
      : 'border-slate-700 bg-slate-800 text-slate-300';

  return (
    <div className="rounded-2xl border border-grid bg-panel/80 p-5 shadow-glow">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Autonomous Scheduler</h2>
          <p className="mt-2 text-sm text-slate-400">NSE trading window, scheduler health, and next open times for the active strategy.</p>
        </div>
        <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${statusClass}`}>{scheduler.status.replace(/_/g, ' ')}</span>
      </div>
      <div className="mt-5 grid gap-3 text-sm text-slate-300">
        <div className="flex justify-between"><span>Trading Window</span><span>{scheduler.tradingWindow}</span></div>
        <div className="flex justify-between"><span>Last Run</span><span>{new Date(scheduler.lastRun).toLocaleString('en-IN')}</span></div>
        <div className="flex justify-between"><span>Next Market Open</span><span>{new Date(scheduler.nextMarketOpen).toLocaleString('en-IN')}</span></div>
      </div>
    </div>
  );
}
