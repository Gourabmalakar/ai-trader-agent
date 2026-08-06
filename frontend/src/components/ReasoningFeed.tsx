import type { DashboardData } from '@/types/dashboard';

export function ReasoningFeed({ decisions }: { decisions: DashboardData['decisions'] }) {
  return (
    <div className="rounded-2xl border border-grid bg-panel/80 p-5">
      <h2 className="text-lg font-semibold text-slate-100">Agent Reasoning Feed</h2>
      <div className="mt-4 space-y-3">
        {decisions.map((decision, index) => (
          <div key={decision} className="border-l-2 border-profit/70 bg-terminal/70 p-3 text-sm text-slate-300">
            <span className="mr-2 text-xs text-slate-500">#{index + 1}</span>{decision}
          </div>
        ))}
      </div>
    </div>
  );
}
