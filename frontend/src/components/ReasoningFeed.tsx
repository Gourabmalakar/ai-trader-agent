import type { DashboardData } from '@/types/dashboard';

export function ReasoningFeed({ decisions }: { decisions: DashboardData['decisions'] }) {
  return (
    <div className="rounded-2xl border border-grid bg-panel/80 p-5">
      <h2 className="text-lg font-semibold text-slate-100">Agent Reasoning Feed</h2>
      {decisions.length === 0 ? (
        <div className="mt-6 rounded-2xl border border-slate-800 bg-terminal/60 p-5 text-sm text-slate-400">
          No reasoning data is available. Connect the backend to display the agent's latest strategy commentary and decision logic.
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          {decisions.map((decision, index) => (
            <div key={`${index}-${decision}`} className="border-l-2 border-profit/70 bg-terminal/70 p-3 text-sm text-slate-300">
              <span className="mr-2 text-xs text-slate-500">#{index + 1}</span>{decision}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
