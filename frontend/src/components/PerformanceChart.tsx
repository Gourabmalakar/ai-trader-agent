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
      <div className="min-h-[320px] rounded-2xl border border-grid bg-panel/80 p-5 shadow-glow">
        <div className="text-sm text-slate-400">
          No performance history available. Connect to the backend API for live portfolio and benchmark data.
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[320px] rounded-2xl border border-grid bg-panel/80 p-5 shadow-glow">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">The Race · Agent vs NIFTY 50</h2>
          <p className="text-xs text-slate-400">Growth since the first recorded paper-account snapshot. Both series start at 0%.</p>
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
          <CartesianGrid stroke="#182033" strokeDasharray="3 3" />
          <XAxis dataKey="date" stroke="#64748b" tickLine={false} style={{ fontSize: '11px' }} />
          <YAxis
            stroke="#64748b"
            tickLine={false}
            style={{ fontSize: '11px' }}
            domain={['auto', 'auto']}
            tickFormatter={(val) => `${val.toFixed(1)}%`}
          />
          <Tooltip
            contentStyle={{ background: '#0b1020', border: '1px solid #182033', borderRadius: '12px', color: '#eef4ff' }}
            formatter={(val: any, name: string) => [`${Number(val || 0).toFixed(2)}%`, name]}
          />
          <Line type="monotone" name="AI Agent" dataKey="portfolio" stroke="#00ff9c" strokeWidth={2.5} dot={false} />
          <Line type="monotone" name="NIFTY 50" dataKey="benchmark" stroke="#8b5cf6" strokeWidth={2.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
