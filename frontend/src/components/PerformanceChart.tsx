'use client';

import { useState } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { DashboardData } from '@/types/dashboard';

type Timeframe = '1D' | '1W' | '1M' | '3M' | '1Y' | 'ALL';

export function PerformanceChart({ data }: { data: DashboardData['performance'] }) {
  const [timeframe, setTimeframe] = useState<Timeframe>('1M');

  // Filter data based on selected timeframe
  const getFilteredData = () => {
    if (!data || data.length === 0) return [];
    if (timeframe === '1D') return data.slice(-2);
    if (timeframe === '1W') return data.slice(-7);
    if (timeframe === '1M') return data.slice(-30);
    if (timeframe === '3M') return data.slice(-90);
    if (timeframe === '1Y') return data.slice(-365);
    return data;
  };

  const chartData = getFilteredData();

  if (chartData.length === 0) {
    return (
      <div className="min-h-[320px] rounded-[1.75rem] border border-white/8 bg-white/[0.04] p-5">
        <div className="text-sm text-slate-400">
          No performance history available. Connect to the backend API for live portfolio and benchmark data.
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[320px] rounded-[1.75rem] border border-white/8 bg-white/[0.04] p-5 shadow-[0_24px_80px_rgba(0,0,0,0.22)]">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Rs 1 CR race: agent vs NIFTY</h2>
          <p className="text-xs text-slate-400">Absolute portfolio value over time, starting from the paper account inception value.</p>
        </div>
        <div className="flex gap-1.5 rounded-xl border border-grid bg-terminal/80 p-1">
          {(['1D', '1W', '1M', '3M', '1Y', 'ALL'] as Timeframe[]).map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                timeframe === tf
                  ? 'border border-profit/40 bg-profit/20 text-profit'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height="78%">
        <LineChart data={chartData}>
          <CartesianGrid stroke="rgba(148,163,184,0.12)" strokeDasharray="3 3" />
          <XAxis dataKey="date" stroke="#64748b" tickLine={false} style={{ fontSize: '11px' }} />
          <YAxis
            stroke="#64748b"
            tickLine={false}
            style={{ fontSize: '11px' }}
            domain={['auto', 'auto']}
            tickFormatter={(val) => `₹${Number(val).toLocaleString('en-IN')}`}
          />
          <Tooltip
            contentStyle={{ background: '#0b1020', border: '1px solid rgba(148,163,184,0.2)', borderRadius: '12px', color: '#eef4ff' }}
            formatter={(val, name) => [`₹${Number(val || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`, String(name ?? '')]}
          />
          <Line type="monotone" name="AI Agent" dataKey="portfolioValue" stroke="#22c55e" strokeWidth={2.5} dot={false} />
          <Line type="monotone" name="NIFTY" dataKey="benchmarkValue" stroke="#f59e0b" strokeWidth={2.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
