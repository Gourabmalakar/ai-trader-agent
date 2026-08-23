'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

const REFRESH_INTERVAL_MS = 30_000;

export function DashboardRefresh() {
  const router = useRouter();
  const [secondsSinceRefresh, setSecondsSinceRefresh] = useState(0);

  useEffect(() => {
    const refreshInterval = window.setInterval(() => {
      router.refresh();
      setSecondsSinceRefresh(0);
    }, REFRESH_INTERVAL_MS);
    const tickInterval = window.setInterval(() => setSecondsSinceRefresh((value) => value + 1), 1_000);
    return () => {
      window.clearInterval(refreshInterval);
      window.clearInterval(tickInterval);
    };
  }, [router]);

  return (
    <div className="fixed bottom-4 left-4 z-40 flex items-center gap-2 rounded-full border border-white/10 bg-black/60 px-3 py-1.5 text-[11px] text-slate-300 backdrop-blur">
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
      </span>
      Live · refreshed {secondsSinceRefresh}s ago
    </div>
  );
}
