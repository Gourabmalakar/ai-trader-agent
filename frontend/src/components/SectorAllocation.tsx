'use client';

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import type { DashboardData } from '@/types/dashboard';

const COLORS = ['#22c55e', '#f59e0b', '#38bdf8', '#a78bfa', '#f472b6', '#fb923c', '#2dd4bf', '#818cf8', '#facc15', '#4ade80'];
const CASH_COLOR = '#475569';

export function SectorAllocation({ allocation }: { allocation?: DashboardData['sectorAllocation'] }) {
  const rows = (allocation ?? []).filter((row) => row.weightPct > 0.05);

  return (
    <div className="rounded-[1.75rem] border border-white/8 bg-white/[0.04] p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-100">Sector allocation</h2>
        <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] uppercase tracking-[0.3em] text-slate-400">Where the book is</span>
      </div>
      {rows.length === 0 ? (
        <div className="mt-6 rounded-2xl border border-white/8 bg-black/20 p-5 text-sm text-slate-400">
          No positions are open yet — the whole book is in cash.
        </div>
      ) : (
        <div className="mt-4 grid gap-4 sm:grid-cols-[1fr_1.1fr] sm:items-center">
          <div className="h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={rows} dataKey="weightPct" nameKey="sector" innerRadius={55} outerRadius={90} paddingAngle={2} stroke="none">
                  {rows.map((row, index) => (
                    <Cell key={row.sector} fill={row.sector === 'Cash' ? CASH_COLOR : COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value) => [`${Number(value).toFixed(1)}%`, 'Weight']}
                  contentStyle={{ background: '#0b1020', border: '1px solid rgba(148,163,184,0.2)', borderRadius: '12px', color: '#eef4ff' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="space-y-2">
            {rows.map((row, index) => (
              <div key={row.sector} className="flex items-center justify-between gap-3 rounded-xl border border-white/8 bg-black/20 px-3 py-2 text-sm">
                <span className="flex items-center gap-2 text-slate-300">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: row.sector === 'Cash' ? CASH_COLOR : COLORS[index % COLORS.length] }} />
                  {row.sector}
                </span>
                <span className="tabular-nums font-semibold text-slate-100">{row.weightPct.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
