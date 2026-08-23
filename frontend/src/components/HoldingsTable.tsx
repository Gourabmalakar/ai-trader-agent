import type { DashboardData } from '@/types/dashboard';
import { formatInr } from '@/lib/format';

export function HoldingsTable({ holdings }: { holdings: DashboardData['holdings'] }) {
  return (
    <div className="rounded-[1.75rem] border border-white/8 bg-white/[0.04] p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-100">Current holdings</h2>
        <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] uppercase tracking-[0.3em] text-slate-400">Live weights</span>
      </div>
      {holdings.length === 0 ? (
        <div className="mt-6 rounded-2xl border border-white/8 bg-black/20 p-5 text-sm text-slate-400">
          No holdings are available. Ensure the backend is running to display live positions.
        </div>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-[0.25em] text-slate-500">
              <tr><th>Symbol</th><th>Sector</th><th>Weight</th><th>P&L</th><th>Conviction</th></tr>
            </thead>
            <tbody className="divide-y divide-grid">
              {holdings.map((holding) => (
                <tr key={holding.symbol} className="text-slate-200">
                  <td className="py-3"><span className="font-semibold text-profit">{holding.symbol}</span><span className="block text-xs text-slate-500">{holding.name}</span></td>
                  <td className="text-xs text-slate-400">{holding.sector ?? '—'}</td>
                  <td>{holding.weight.toFixed(1)}%</td>
                  <td className={holding.pnl >= 0 ? 'text-profit' : 'text-loss'}>{formatInr(holding.pnl)}</td>
                  <td>{Math.round(holding.conviction * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
