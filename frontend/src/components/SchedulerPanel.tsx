import type { DashboardData } from '@/types/dashboard';

export function SchedulerPanel({ scheduler }: { scheduler: DashboardData['scheduler'] }) {
  return (
    <div className="rounded-2xl border border-grid bg-panel/80 p-5">
      <h2 className="text-lg font-semibold text-slate-100">Autonomous Scheduler</h2>
      <div className="mt-4 grid gap-3 text-sm text-slate-300">
        <div className="flex justify-between"><span>Status</span><span className="font-semibold text-profit">{scheduler.status}</span></div>
        <div className="flex justify-between"><span>Trading Window</span><span>{scheduler.tradingWindow}</span></div>
        <div className="flex justify-between"><span>Last Run</span><span>{new Date(scheduler.lastRun).toLocaleString('en-IN')}</span></div>
        <div className="flex justify-between"><span>Next Market Open</span><span>{new Date(scheduler.nextMarketOpen).toLocaleString('en-IN')}</span></div>
      </div>
    </div>
  );
}
