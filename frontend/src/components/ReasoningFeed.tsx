import type { DashboardData } from '@/types/dashboard';

const PROVIDER_CLASS: Record<string, string> = {
  gemini: 'text-emerald-300',
  claude: 'text-violet-300',
  quant_only: 'text-slate-500',
  risk_stop_loss: 'text-rose-300',
  risk_take_profit: 'text-sky-300',
};

function parseProvider(line: string): { provider: string | null; text: string } {
  const match = line.match(/\[(gemini|claude|quant_only|risk_stop_loss|risk_take_profit)\]\s*·?\s*/);
  if (!match) return { provider: null, text: line };
  return { provider: match[1], text: line.replace(match[0], '') };
}

export function ReasoningFeed({ decisions }: { decisions: DashboardData['decisions'] }) {
  return (
    <div className="rounded-[1.75rem] border border-white/8 bg-white/[0.04] p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-100">Reasoning feed</h2>
        <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] uppercase tracking-[0.3em] text-slate-400">Latest signals</span>
      </div>
      {decisions.length === 0 ? (
        <div className="mt-6 rounded-2xl border border-white/8 bg-black/20 p-5 text-sm text-slate-400">
          No reasoning data is available yet. The next scheduled trading cycle will populate this feed with the agent's live decision log.
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          {decisions.map((decision, index) => {
            const { provider, text } = parseProvider(decision);
            return (
              <div key={`${index}-${decision}`} className="rounded-2xl border border-white/8 bg-black/20 p-4 text-sm text-slate-300">
                <span className="mr-2 text-xs uppercase tracking-[0.25em] text-emerald-300">#{index + 1}</span>
                {provider && <span className={`mr-2 text-xs font-semibold uppercase tracking-[0.15em] ${PROVIDER_CLASS[provider]}`}>{provider.replace('_', '-')}</span>}
                {text}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
