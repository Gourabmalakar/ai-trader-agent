import type { DashboardData } from '@/types/dashboard';
import { formatInr } from '@/lib/format';

export function HoldingsTable({ holdings }: { holdings: DashboardData['holdings'] }) {
  return (
    <div className="rounded-2xl border border-grid bg-panel/80 p-5">
      <h2 className="text-lg font-semibold text-slate-100">Portfolio Holdings</h2>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs uppercase tracking-widest text-slate-500">
            <tr><th>Symbol</th><th>Weight</th><th>P&L</th><th>Risk</th><th>Conviction</th></tr>
          </thead>
          <tbody className="divide-y divide-grid">
            {holdings.map((holding) => (
              <tr key={holding.symbol} className="text-slate-200">
                <td className="py-3"><span className="font-semibold text-profit">{holding.symbol}</span><span className="block text-xs text-slate-500">{holding.name}</span></td>
                <td>{holding.weight.toFixed(1)}%</td>
                <td className={holding.pnl >= 0 ? 'text-profit' : 'text-loss'}>{formatInr(holding.pnl)}</td>
                <td>{holding.risk}</td>
                <td>{Math.round(holding.conviction * 100)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
