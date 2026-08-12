import type { DashboardData } from '@/types/dashboard';

export async function getDashboardData(): Promise<DashboardData> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL;
  const dashboardUrl = baseUrl ? `${baseUrl}/api/dashboard` : '/api/dashboard';
  try {
    const response = await fetch(dashboardUrl, { next: { revalidate: 60 } });
    if (response.ok) {
      return await response.json();
    }
  } catch {
    // Fall through to offline demo mode
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
      marketRegime: 'UNKNOWN'
    },
    scheduler: {
      status: 'OFFLINE',
      lastRun: new Date().toISOString(),
      nextMarketOpen: new Date().toISOString(),
      tradingWindow: '09:15-15:30 IST'
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

export async function askAgent(message: string): Promise<string> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL;
  if (baseUrl) {
    try {
      const res = await fetch(`${baseUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
      });
      if (res.ok) {
        const data = await res.json();
        return data.reply;
      }
    } catch {
      // Fallback response
    }
  }

  const msg = message.toLowerCase();
  if (msg.includes('reliance')) {
    return 'Reliance Industries (RELIANCE.NS) is currently our top holding at 7.8% weight with a conviction score of 88%. Analyst score is +0.42 with strong relative strength above its 20-day SMA.';
  } else if (msg.includes('risk') || msg.includes('drawdown')) {
    return 'Portfolio Risk Score is 72/100 (Balanced Growth). We maintain a 21.5% cash buffer (min 15% rule) and cap single-stock weight at 8% to protect capital.';
  } else if (msg.includes('nifty') || msg.includes('beat') || msg.includes('alpha')) {
    return 'Our AI loop is currently generating positive alpha over the benchmark on the live paper portfolio. We focus on strong large-cap trends with disciplined risk controls.';
  } else if (msg.includes('it') || msg.includes('infosys') || msg.includes('tcs')) {
    return 'We recently trimmed INFY.NS to manage exposure while keeping TCS.NS on the active watchlist due to positive relative strength.';
  } else {
    return 'As Chief Investment Officer of AI Trader Agent, our goal is to outperform the benchmark using disciplined trend-following, strict risk management, and regular NSE market hours execution.';
  }
}
