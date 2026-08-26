'use client';

import { useEffect, useState } from 'react';
import { getBackendBaseUrl } from '@/lib/api';

type TradeRow = {
  time: string;
  symbol: string;
  name: string;
  side: string;
  quantity: number;
  price: number;
  costBasis?: number | null;
  realizedPnl?: number | null;
  reason: string;
  status: string;
  provider: string;
};

type TradesResponse = {
  trades: TradeRow[];
  page: number;
  pageSize: number;
  totalCount: number;
  totalPages: number;
};

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

const PAGE_SIZE = 25;

export function TradeLog() {
  const [page, setPage] = useState(1);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [data, setData] = useState<TradesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const baseUrl = getBackendBaseUrl();

  useEffect(() => {
    if (!baseUrl) {
      setLoading(false);
      setError(true);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    const params = new URLSearchParams({ page: String(page), pageSize: String(PAGE_SIZE) });
    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo) params.set('date_to', dateTo);
    fetch(`${baseUrl}/api/trades?${params.toString()}`, { signal: controller.signal })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error('failed'))))
      .then((json: TradesResponse) => {
        setData(json);
        setError(false);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [baseUrl, page, dateFrom, dateTo]);

  const downloadUrl = baseUrl
    ? `${baseUrl}/api/trades?format=xlsx${dateFrom ? `&date_from=${dateFrom}` : ''}${dateTo ? `&date_to=${dateTo}` : ''}`
    : null;

  return (
    <div className="rounded-[1.75rem] border border-white/8 bg-white/[0.04] p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Trade &amp; decision log</h2>
          <p className="mt-1 text-xs text-slate-500">Every order the agent attempted, filled or rejected, with the reasoning behind it.</p>
        </div>
        <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] uppercase tracking-[0.3em] text-slate-400">
          {data ? `${data.totalCount} total` : '…'}
        </span>
      </div>

      <div className="mt-4 flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          From
          <input
            type="date"
            value={dateFrom}
            onChange={(event) => {
              setDateFrom(event.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-white/10 bg-black/30 px-2 py-1.5 text-sm text-slate-200"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          To
          <input
            type="date"
            value={dateTo}
            onChange={(event) => {
              setDateTo(event.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-white/10 bg-black/30 px-2 py-1.5 text-sm text-slate-200"
          />
        </label>
        {(dateFrom || dateTo) && (
          <button
            onClick={() => {
              setDateFrom('');
              setDateTo('');
              setPage(1);
            }}
            className="rounded-lg border border-white/10 bg-black/20 px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200"
          >
            Clear
          </button>
        )}
        {downloadUrl && (
          <a
            href={downloadUrl}
            className="ml-auto rounded-lg border border-emerald-400/30 bg-emerald-400/10 px-3 py-1.5 text-xs font-semibold text-emerald-200 hover:bg-emerald-400/20"
          >
            Download Excel
          </a>
        )}
      </div>

      {loading && <p className="mt-6 text-sm text-slate-500">Loading…</p>}
      {!loading && error && <p className="mt-6 text-sm text-slate-500">Could not reach the backend for the trade log.</p>}
      {!loading && !error && data && data.trades.length === 0 && (
        <p className="mt-6 text-sm text-slate-500">No trades match this filter yet.</p>
      )}

      {!loading && !error && data && data.trades.length > 0 && (
        <>
          <div className="mt-4 space-y-3">
            {data.trades.map((trade, index) => (
              <div key={`${trade.time}-${trade.symbol}-${index}`} className="rounded-2xl border border-white/8 bg-black/20 p-4 text-sm">
                <div className="flex items-center justify-between">
                  <span className={trade.side === 'BUY' ? 'font-semibold text-emerald-300' : 'font-semibold text-amber-300'}>
                    {trade.side} {trade.symbol} <span className="font-normal text-slate-500">({trade.name})</span>
                  </span>
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
                  <span className="text-xs uppercase tracking-[0.22em] text-slate-500">{trade.status}</span>
                  <ProviderBadge provider={trade.provider} />
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-400">{trade.reason}</p>
              </div>
            ))}
          </div>

          <div className="mt-4 flex items-center justify-between text-sm text-slate-400">
            <button
              onClick={() => setPage((value) => Math.max(1, value - 1))}
              disabled={page <= 1}
              className="rounded-lg border border-white/10 bg-black/20 px-3 py-1.5 disabled:opacity-30"
            >
              Previous
            </button>
            <span>
              Page {data.page} of {data.totalPages}
            </span>
            <button
              onClick={() => setPage((value) => Math.min(data.totalPages, value + 1))}
              disabled={page >= data.totalPages}
              className="rounded-lg border border-white/10 bg-black/20 px-3 py-1.5 disabled:opacity-30"
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
