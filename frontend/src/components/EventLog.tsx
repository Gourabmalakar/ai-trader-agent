'use client';

import { useEffect, useState } from 'react';
import { getBackendBaseUrl } from '@/lib/api';

type EventRow = {
  eventType: string;
  payload: Record<string, unknown>;
  createdAt: string;
};

type EventsResponse = {
  events: EventRow[];
  page: number;
  pageSize: number;
  totalCount: number;
  totalPages: number;
};

const EVENT_TYPES = ['cycle_run', 'email_sent', 'decision', 'trade'] as const;

function StatusBadge({ payload }: { payload: Record<string, unknown> }) {
  const status = payload.status as string | undefined;
  if (!status) return null;
  const isSuccess = status === 'success';
  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] ${
        isSuccess ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200' : 'border-rose-400/30 bg-rose-400/10 text-rose-200'
      }`}
    >
      {status}
    </span>
  );
}

function summarize(row: EventRow): string {
  const p = row.payload;
  if (row.eventType === 'cycle_run') {
    return p.status === 'success' ? `Engine: ${p.engineProvider ?? 'unknown'} · Market: ${p.marketStatus ?? 'unknown'}` : `Error: ${p.error ?? 'unknown error'}`;
  }
  if (row.eventType === 'email_sent') {
    return `${String(p.kind ?? 'email').toUpperCase()} email${p.error ? ` — ${p.error}` : ''}`;
  }
  if (row.eventType === 'decision' || row.eventType === 'trade') {
    return `${p.symbol ?? ''} ${p.action ?? p.side ?? ''}`.trim();
  }
  return JSON.stringify(p).slice(0, 120);
}

const PAGE_SIZE = 25;

export function EventLog() {
  const [page, setPage] = useState(1);
  const [selectedTypes, setSelectedTypes] = useState<string[]>(['cycle_run', 'email_sent']);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [onlyFailures, setOnlyFailures] = useState(false);
  const [data, setData] = useState<EventsResponse | null>(null);
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
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
    selectedTypes.forEach((type) => params.append('event_type', type));
    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo) params.set('date_to', dateTo);
    fetch(`${baseUrl}/api/events?${params.toString()}`, { signal: controller.signal })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error('failed'))))
      .then((json: EventsResponse) => {
        setData(json);
        setError(false);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [baseUrl, page, selectedTypes, dateFrom, dateTo]);

  const toggleType = (type: string) => {
    setPage(1);
    setSelectedTypes((current) => (current.includes(type) ? current.filter((t) => t !== type) : [...current, type]));
  };

  const visibleEvents = data ? (onlyFailures ? data.events.filter((e) => e.payload.status === 'failure') : data.events) : [];

  return (
    <div className="rounded-[1.75rem] border border-white/8 bg-white/[0.04] p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">System event log</h2>
          <p className="mt-1 text-xs text-slate-500">Every cycle run and notification email, success or failure — the source of truth for whether automation is actually firing.</p>
        </div>
        <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] uppercase tracking-[0.3em] text-slate-400">
          {data ? `${data.totalCount} total` : '…'}
        </span>
      </div>

      <div className="mt-4 flex flex-wrap items-end gap-3">
        <div className="flex flex-wrap gap-2">
          {EVENT_TYPES.map((type) => (
            <button
              key={type}
              onClick={() => toggleType(type)}
              className={`rounded-full border px-3 py-1 text-xs ${
                selectedTypes.includes(type) ? 'border-emerald-400/40 bg-emerald-400/10 text-emerald-200' : 'border-white/10 bg-black/20 text-slate-400'
              }`}
            >
              {type.replace('_', ' ')}
            </button>
          ))}
        </div>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          From
          <input type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(1); }} className="rounded-lg border border-white/10 bg-black/30 px-2 py-1.5 text-sm text-slate-200" />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          To
          <input type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(1); }} className="rounded-lg border border-white/10 bg-black/30 px-2 py-1.5 text-sm text-slate-200" />
        </label>
        <label className="flex items-center gap-2 rounded-lg border border-white/10 bg-black/20 px-3 py-1.5 text-xs text-slate-300">
          <input type="checkbox" checked={onlyFailures} onChange={(e) => setOnlyFailures(e.target.checked)} />
          Failures only
        </label>
      </div>

      {loading && <p className="mt-6 text-sm text-slate-500">Loading…</p>}
      {!loading && error && <p className="mt-6 text-sm text-slate-500">Could not reach the backend for the event log.</p>}
      {!loading && !error && data && visibleEvents.length === 0 && <p className="mt-6 text-sm text-slate-500">No events match this filter.</p>}

      {!loading && !error && data && visibleEvents.length > 0 && (
        <>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-[0.25em] text-slate-500">
                <tr>
                  <th className="pb-2">Time</th>
                  <th className="pb-2">Event</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2">Detail</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {visibleEvents.map((row, index) => (
                  <tr key={`${row.createdAt}-${index}`} className="text-slate-300">
                    <td className="py-2 pr-3 whitespace-nowrap text-slate-500">{new Date(row.createdAt).toLocaleString('en-IN')}</td>
                    <td className="py-2 pr-3 whitespace-nowrap">{row.eventType.replace('_', ' ')}</td>
                    <td className="py-2 pr-3"><StatusBadge payload={row.payload} /></td>
                    <td className="py-2 text-slate-400">{summarize(row)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex items-center justify-between text-sm text-slate-400">
            <button onClick={() => setPage((v) => Math.max(1, v - 1))} disabled={page <= 1} className="rounded-lg border border-white/10 bg-black/20 px-3 py-1.5 disabled:opacity-30">
              Previous
            </button>
            <span>Page {data.page} of {data.totalPages}</span>
            <button onClick={() => setPage((v) => Math.min(data.totalPages, v + 1))} disabled={page >= data.totalPages} className="rounded-lg border border-white/10 bg-black/20 px-3 py-1.5 disabled:opacity-30">
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
