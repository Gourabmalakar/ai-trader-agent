import type { DashboardData } from '@/types/dashboard';

type NewsItem = NonNullable<DashboardData['marketIntelligence']>['items'][number];

export function MarketIntelligence({ items }: { items: NewsItem[] }) {
  return (
    <div className="rounded-2xl border border-grid bg-panel/80 p-5">
      <h2 className="text-lg font-semibold text-slate-100">Market Intelligence</h2>
      <div className="mt-4 space-y-3">
        {items.map((item) => (
          <div key={`${item.source}-${item.title}`} className="rounded-xl border border-grid bg-terminal/80 p-3 text-sm">
            <div className="flex items-center justify-between gap-3">
              <span className="font-semibold text-slate-100">{item.title}</span>
              <span className={item.impact === 'HIGH_RISK' ? 'text-loss' : item.impact === 'POSITIVE' ? 'text-profit' : 'text-amber'}>{item.impact}</span>
            </div>
            <p className="mt-2 text-slate-400">{item.summary}</p>
            <p className="mt-2 text-xs uppercase tracking-widest text-slate-600">{item.category} · {item.source}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
