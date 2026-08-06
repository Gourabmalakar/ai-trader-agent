import type { DashboardData } from '@/types/dashboard';

export function TradeBlotter({ trades }: { trades: DashboardData['trades'] }) {
  return (
    <div className="rounded-2xl border border-grid bg-panel/80 p-5">
      <h2 className="text-lg font-semibold text-slate-100">Trade Blotter</h2>
      <div className="mt-4 space-y-3">
        {trades.map((trade) => (
          <div key={`${trade.time}-${trade.symbol}`} className="rounded-xl bg-terminal/80 p-3 text-sm">
            <div className="flex items-center justify-between">
              <span className={trade.side === 'BUY' ? 'font-semibold text-profit' : 'font-semibold text-amber'}>{trade.side} {trade.symbol}</span>
              <span className="text-slate-500">{new Date(trade.time).toLocaleString('en-IN')}</span>
            </div>
            <p className="mt-2 text-slate-300">Qty {trade.quantity} @ ₹{trade.price.toFixed(2)}</p>
            <p className="mt-1 text-xs text-slate-500">{trade.reason}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
