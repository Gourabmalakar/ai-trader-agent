import type { DashboardData } from '@/types/dashboard';

function NoteCard({ label, note, pendingMessage }: { label: string; note?: { text: string; provider: string; generatedAt: string } | null; pendingMessage: string }) {
  return (
    <div className="rounded-2xl border border-white/8 bg-black/20 p-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-100">{label}</h3>
        {note && (
          <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] uppercase tracking-[0.2em] text-slate-400">
            {note.provider} · {new Date(note.generatedAt).toLocaleDateString('en-IN')}
          </span>
        )}
      </div>
      {note ? (
        <p className="mt-3 text-sm leading-7 text-slate-300 whitespace-pre-line">{note.text}</p>
      ) : (
        <p className="mt-3 text-sm leading-6 text-slate-500">{pendingMessage}</p>
      )}
    </div>
  );
}

export function ResearchNotes({ research }: { research: DashboardData['research'] }) {
  return (
    <div className="rounded-[1.75rem] border border-white/8 bg-white/[0.04] p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-100">Research desk</h2>
        <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] uppercase tracking-[0.3em] text-slate-400">CIO notes</span>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <NoteCard label="Weekly market outlook" note={research?.weekly} pendingMessage="Not published yet — generated automatically every Friday at market close." />
        <NoteCard label="Monthly portfolio review" note={research?.monthly} pendingMessage="Not published yet — generated automatically on the last trading day of each month at market close." />
      </div>
    </div>
  );
}
