'use client';

import { useState } from 'react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
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

  return (
    <div className="h-88 rounded-2xl border border-grid bg-panel/80 p-5 shadow-glow">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Portfolio vs NIFTY 50 Benchmark</h2>
          <p className="text-xs text-slate-400">Paper Capital: ₹1,00,00,000 · Outperformance (Alpha) tracking</p>
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
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="portfolioGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#00ff9c" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#00ff9c" stopOpacity={0.0} />
            </linearGradient>
            <linearGradient id="benchmarkGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ffb000" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#ffb000" stopOpacity={0.0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#182033" strokeDasharray="3 3" />
          <XAxis dataKey="date" stroke="#64748b" tickLine={false} style={{ fontSize: '11px' }} />
          <YAxis
            stroke="#64748b"
            tickLine={false}
            style={{ fontSize: '11px' }}
            domain={['auto', 'auto']}
            tickFormatter={(val) => `₹${(val / 100000).toFixed(1)}L`}
          />
          <Tooltip
            contentStyle={{ background: '#0b1020', border: '1px solid #182033', borderRadius: '12px', color: '#eef4ff' }}
            formatter={(val: any) => [`₹${Number(val || 0).toLocaleString('en-IN')}`, 'Value']}
          />
          <Area type="monotone" name="Portfolio (₹1 Cr Base)" dataKey="portfolio" stroke="#00ff9c" strokeWidth={2} fill="url(#portfolioGrad)" />
          <Area type="monotone" name="Nifty 50 Benchmark" dataKey="benchmark" stroke="#ffb000" strokeWidth={2} fill="url(#benchmarkGrad)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
