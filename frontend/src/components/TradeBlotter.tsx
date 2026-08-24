import type { DashboardData } from '@/types/dashboard';

const PROVIDER_LABEL: Record<string, string> = {
  gemini: 'Gemini',
  claude: 'Claude (fallback)',
  quant_only: 'Quant-only',
  risk_stop_loss: 'Stop-loss',
  risk_take_profit: 'Take-profit',
};

const PROVIDER_CLASS: Record<string, string> = {
  gemini: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200',
  claude: 'border-violet-400/30 bg-violet-400/10 text-violet-200',
  quant_only: 'border-white/10 bg-black/20 text-slate-400',
  risk_stop_loss: 'border-rose-400/30 bg-rose-400/10 text-rose-200',
  risk_take_profit: 'border-sky-400/30 bg-sky-400/10 text-sky-200',
};

function ProviderBadge({ provider }: { provider?: string }) {
  const key = provider ?? 'quant_only';
  return (
    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] ${PROVIDER_CLASS[key] ?? PROVIDER_CLASS.quant_only}`}>
      {PROVIDER_LABEL[key] ?? key}
    </span>
  );
}

export function TradeBlotter({ trades }: { trades: DashboardData['trades'] }) {
  return (
    <div className="rounded-[1.75rem] border border-white/8 bg-white/[0.04] p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-100">Trade journal</h2>
        <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] uppercase tracking-[0.3em] text-slate-400">Decision trail</span>
      </div>
      {trades.length === 0 ? (
        <div className="mt-6 rounded-2xl border border-white/8 bg-black/20 p-5 text-sm text-slate-400">
          No recent trades available. Start the backend to populate live execution history.
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          {trades.map((trade) => (
            <div key={`${trade.time}-${trade.symbol}`} className="rounded-2xl border border-white/8 bg-black/20 p-4 text-sm">
              <div className="flex items-center justify-between">
                <span className={trade.side === 'BUY' ? 'font-semibold text-emerald-300' : 'font-semibold text-amber-300'}>{trade.side} {trade.symbol}</span>
                <span className="text-slate-500">{new Date(trade.time).toLocaleString('en-IN')}</span>
              </div>
              <p className="mt-2 text-slate-300">
                {trade.side === 'SELL' && trade.costBasis != null
                  ? `Bought at ₹${trade.costBasis.toFixed(2)}, sold ${trade.quantity} @ ₹${trade.price.toFixed(2)}`
                  : `Qty ${trade.quantity} @ ₹${trade.price.toFixed(2)}`}
              </p>
              {trade.realizedPnl != null && (
                <p className={`mt-1 text-sm font-semibold ${trade.realizedPnl >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                  Net P&L: {trade.realizedPnl >= 0 ? '+' : ''}₹{trade.realizedPnl.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                </p>
              )}
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span className="text-xs uppercase tracking-[0.22em] text-slate-500">{trade.status ?? 'FILLED_PAPER'}</span>
                <ProviderBadge provider={trade.provider} />
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-400">{trade.reason}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
