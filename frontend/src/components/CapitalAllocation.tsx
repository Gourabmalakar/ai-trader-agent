import type { DashboardData } from '@/types/dashboard';
import { formatInr } from '@/lib/format';

const STANCE_LABEL: Record<string, string> = {
  'under-deployed': 'Holding more cash than the regime target',
  'over-deployed': 'Deployed more than the regime target',
  'in line': 'In line with the regime target',
};

export function CapitalAllocation({ allocation }: { allocation?: DashboardData['capitalAllocation'] }) {
  if (!allocation) return null;
  const { recommendedExposurePct, actualDeployedPct, cashReservePct, cashReserveValue, deployedValue, allocationStance, realizedPnl, unrealizedPnl, rationale, marketRegime } = allocation;

  return (
    <div className="rounded-[1.75rem] border border-white/8 bg-white/[0.04] p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-100">Capital allocation</h2>
        <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] uppercase tracking-[0.3em] text-slate-400">{marketRegime?.replaceAll('_', ' ')}</span>
      </div>

      <div className="mt-4 space-y-2">
        <div className="flex items-center gap-3">
          <span className="w-28 shrink-0 text-[11px] uppercase tracking-[0.18em] text-slate-400">Deployed</span>
          <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-white/5">
            <div className="h-full rounded-full bg-emerald-400" style={{ width: `${Math.min(100, Math.max(0, actualDeployedPct))}%` }} />
          </div>
          <span className="w-14 shrink-0 text-right text-sm tabular-nums text-slate-200">{actualDeployedPct.toFixed(0)}%</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="w-28 shrink-0 text-[11px] uppercase tracking-[0.18em] text-slate-400">Regime target</span>
          <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-white/5">
            <div className="h-full rounded-full bg-amber-400/70" style={{ width: `${Math.min(100, Math.max(0, recommendedExposurePct))}%` }} />
          </div>
          <span className="w-14 shrink-0 text-right text-sm tabular-nums text-slate-200">{recommendedExposurePct.toFixed(0)}%</span>
        </div>
      </div>
      <p className="mt-2 text-xs uppercase tracking-[0.2em] text-slate-500">{STANCE_LABEL[allocationStance] ?? allocationStance}</p>

      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-2xl border border-white/8 bg-black/20 p-3">
          <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Cash reserve</p>
          <p className="mt-1 text-sm font-semibold text-slate-100">{formatInr(cashReserveValue)}</p>
          <p className="text-xs text-slate-500">{cashReservePct.toFixed(0)}% of book</p>
        </div>
        <div className="rounded-2xl border border-white/8 bg-black/20 p-3">
          <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Deployed</p>
          <p className="mt-1 text-sm font-semibold text-slate-100">{formatInr(deployedValue)}</p>
        </div>
        <div className="rounded-2xl border border-white/8 bg-black/20 p-3">
          <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Realized P&L</p>
          <p className={`mt-1 text-sm font-semibold ${realizedPnl >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>{realizedPnl >= 0 ? '+' : ''}{formatInr(realizedPnl)}</p>
        </div>
        <div className="rounded-2xl border border-white/8 bg-black/20 p-3">
          <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Unrealized P&L</p>
          <p className={`mt-1 text-sm font-semibold ${unrealizedPnl >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>{unrealizedPnl >= 0 ? '+' : ''}{formatInr(unrealizedPnl)}</p>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-white/8 bg-black/20 p-3 text-xs leading-6 text-slate-400">
        {rationale}
      </div>
    </div>
  );
}
