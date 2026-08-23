import type { DashboardData } from '@/types/dashboard';

export function GovernancePanel({ governance }: { governance?: DashboardData['governance'] }) {
  if (!governance) return null;
  const isClean = governance.status === 'CLEAN';

  return (
    <div className="rounded-[1.75rem] border border-white/8 bg-white/[0.04] p-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Governance &amp; compliance</h2>
          <p className="mt-1 text-xs text-slate-500">An independent, automated re-check of every fill against the fund&apos;s own rules — run fresh on every load, not just a self-report from the trading logic.</p>
        </div>
        <span className={`shrink-0 rounded-full border px-3 py-1 text-xs font-semibold ${isClean ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200' : 'border-rose-400/30 bg-rose-400/10 text-rose-200'}`}>
          {isClean ? 'Clean' : `${governance.violations.length} issue(s) found`}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 text-sm text-slate-300">
        <div className="flex justify-between rounded-xl border border-white/8 bg-black/20 p-3"><span>Trades audited</span><span className="font-semibold text-slate-100">{governance.auditedTrades}</span></div>
        <div className="flex justify-between rounded-xl border border-white/8 bg-black/20 p-3"><span>Snapshots audited</span><span className="font-semibold text-slate-100">{governance.auditedSnapshots}</span></div>
      </div>

      {!isClean && (
        <div className="mt-4 space-y-2">
          {governance.violations.map((v, i) => (
            <div key={i} className="rounded-xl border border-rose-400/20 bg-rose-400/5 p-3 text-xs text-rose-200">
              <span className="font-semibold uppercase tracking-[0.15em]">{v.rule}</span> · {v.subject} — {v.detail}
            </div>
          ))}
        </div>
      )}

      <details className="mt-4 rounded-xl border border-white/8 bg-black/20 p-3 text-xs text-slate-400">
        <summary className="cursor-pointer text-slate-300">Rules checked every time</summary>
        <ul className="mt-2 list-disc space-y-1 pl-4">
          {governance.rulesChecked.map((rule) => (
            <li key={rule}>{rule}</li>
          ))}
        </ul>
      </details>
    </div>
  );
}
