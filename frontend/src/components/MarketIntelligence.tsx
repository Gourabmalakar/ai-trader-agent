import type { DashboardData } from '@/types/dashboard';

type NewsItem = NonNullable<DashboardData['marketIntelligence']>['items'][number];

export function MarketIntelligence({ items }: { items: NewsItem[] }) {
  return (
    <div className="rounded-[1.75rem] border border-white/8 bg-white/[0.04] p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-100">Market intelligence</h2>
        <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] uppercase tracking-[0.3em] text-slate-400">Public headlines</span>
      </div>
      {items.length === 0 ? (
        <div className="mt-6 rounded-2xl border border-white/8 bg-black/20 p-5 text-sm text-slate-400">
          Intelligence feeds are not available. Activate the backend to show live market signals and risk alerts.
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          {items.map((item) => (
            <div key={`${item.source}-${item.title}`} className="rounded-2xl border border-white/8 bg-black/20 p-4 text-sm">
              <div className="flex items-center justify-between gap-3">
                <span className="font-semibold text-slate-100">{item.title}</span>
                <span className={item.impact === 'HIGH_RISK' ? 'text-loss' : item.impact === 'POSITIVE' ? 'text-profit' : 'text-amber'}>{item.impact}</span>
              </div>
              <p className="mt-2 text-slate-400">{item.summary}</p>
              <p className="mt-2 text-xs uppercase tracking-widest text-slate-600">{item.category} · {item.source}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
