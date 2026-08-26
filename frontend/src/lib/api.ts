import type { DashboardData } from '@/types/dashboard';

export function getBackendBaseUrl(): string | null {
  return process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL || null;
}

export async function getDashboardData(): Promise<DashboardData> {
  const baseUrl = getBackendBaseUrl();
  if (baseUrl) {
    try {
      const response = await fetch(`${baseUrl}/api/dashboard`, { cache: 'no-store' });
      if (response.ok) {
        return await response.json();
      }
    } catch {
      // Fall through to offline demo mode
    }
  }

  // Fallback demo mode: preserve layout and avoid showing any live-like metrics.
  return {
    portfolio: {
      totalValue: 0,
      cash: 0,
      investedValue: 0,
      dailyPnl: 0,
      totalReturn: 0,
      benchmarkReturn: 0,
      alpha: 0,
      marketRegime: 'UNKNOWN',
      startingCapital: 0,
      inceptionDate: null,
      tradeCount: 0,
      buyCount: 0,
      sellCount: 0,
      cashUtilizationPct: 0,
      deploymentPct: 0,
      openPositions: 0
    },
    comparison: {
      inceptionDate: null,
      startingCapital: 0,
      agentValue: 0,
      agentReturnPct: 0,
      agentProfit: 0,
      niftyValue: 0,
      niftyReturnPct: 0,
      niftyProfit: 0,
      alphaPct: 0
    },
    scheduler: {
      status: 'OFFLINE',
      lastRun: new Date().toISOString(),
      nextMarketOpen: new Date().toISOString(),
      tradingWindow: '09:15-15:30 IST',
      lastAgentCycle: null,
      lastMarketDataAt: null,
      lastNewsAt: null
    },
    holdings: [],
    trades: [],
    performance: [],
    decisions: [],
    marketIntelligence: {
      headlineCount: 0,
      highRiskCount: 0,
      positiveCount: 0,
      items: []
    },
    publicSignals: {
      fundamentals: [],
      headlines: []
    },
    investmentThesis: {
      summary: 'Live strategy data is unavailable. The backend is currently offline or unreachable.',
      focus: ['Backend connection required', 'Healthy fallback state', 'No stale live metrics'],
      watchlist: []
    },
    riskProfile: {
      score: 0,
      posture: 'Offline',
      cashBuffer: 0,
      maxSingleStockWeight: 0,
      maxDailyDeployment: 0,
      notes: ['Start the backend API to load actual portfolio and trading metrics.']
    },
    marketOutlook: {
      summary: 'No market outlook available while the live backend is disconnected.',
      drivers: [],
      bias: 'Offline'
    },
    dataStatus: {
      source: 'No connected backend',
      updatedAt: null,
      message: 'The paper-trading backend is offline.',
      persistence: 'No paper account data is being displayed.'
    },
    isFallback: true
  };
}
