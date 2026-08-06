import type { DashboardData } from '@/types/dashboard';

export async function getDashboardData(): Promise<DashboardData> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL;
  if (baseUrl) {
    try {
      const response = await fetch(`${baseUrl}/api/dashboard`, { next: { revalidate: 30 } });
      if (response.ok) {
        return await response.json();
      }
    } catch {
      // Fallback to standalone simulation
    }
  }

  // Generate robust historical performance curves for 1D, 1W, 1M, 3M, 1Y, ALL
  const now = new Date();
  const generatePerformance = (days: number, dailyDrift: number, volatility: number) => {
    const points = [];
    let pVal = 10000000;
    let bVal = 10000000;
    for (let i = days; i >= 0; i--) {
      const d = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
      const dateStr = d.toISOString().split('T')[0];
      const cycle = Math.sin(i / 3) * volatility;
      pVal = pVal * (1 + dailyDrift + cycle * 0.002);
      bVal = bVal * (1 + (dailyDrift * 0.7) + cycle * 0.0015);
      points.push({
        date: dateStr,
        portfolio: Math.round(pVal),
        benchmark: Math.round(bVal)
      });
    }
    return points;
  };

  const perf1M = generatePerformance(30, 0.0008, 0.6);

  return {
    portfolio: {
      totalValue: 10248500,
      cash: 2150000,
      investedValue: 8098500,
      dailyPnl: 86500,
      totalReturn: 2.485,
      benchmarkReturn: 1.72,
      alpha: 0.765,
      marketRegime: 'RISK_ON_TRENDING'
    },
    scheduler: {
      status: 'AFTER_HOURS',
      lastRun: new Date().toISOString(),
      nextMarketOpen: new Date(Date.now() + 10 * 3600 * 1000).toISOString(),
      tradingWindow: '09:15-15:30 IST'
    },
    holdings: [
      { symbol: 'RELIANCE.NS', name: 'Reliance Industries', weight: 7.8, pnl: 128500, risk: 'Low Risk', conviction: 0.88 },
      { symbol: 'HDFCBANK.NS', name: 'HDFC Bank', weight: 6.2, pnl: 84500, risk: 'Low Risk', conviction: 0.82 },
      { symbol: 'ICICIBANK.NS', name: 'ICICI Bank', weight: 5.9, pnl: 62400, risk: 'Medium Risk', conviction: 0.79 },
      { symbol: 'INFY.NS', name: 'Infosys', weight: 5.4, pnl: -18500, risk: 'Medium Risk', conviction: 0.65 },
      { symbol: 'TCS.NS', name: 'Tata Consultancy Services', weight: 4.8, pnl: 34200, risk: 'Low Risk', conviction: 0.76 },
      { symbol: 'BHARTIARTL.NS', name: 'Bharti Airtel', weight: 4.2, pnl: 41900, risk: 'Low Risk', conviction: 0.84 }
    ],
    trades: [
      { 
        time: new Date().toISOString(), 
        symbol: 'RELIANCE.NS', 
        side: 'BUY', 
        quantity: 42, 
        price: 2894.2, 
        reason: 'Analyst RSI at 63 with relative strength > Nifty 50. Portfolio Manager increased allocation by +1.2%.' 
      },
      { 
        time: new Date(Date.now() - 15 * 60 * 1000).toISOString(), 
        symbol: 'INFY.NS', 
        side: 'SELL', 
        quantity: 18, 
        price: 1531.8, 
        reason: 'Tech sector momentum cooling; Risk Manager enforced position reduction to maintain cash buffer > 15%.' 
      },
      { 
        time: new Date(Date.now() - 45 * 60 * 1000).toISOString(), 
        symbol: 'ICICIBANK.NS', 
        side: 'BUY', 
        quantity: 50, 
        price: 1210.5, 
        reason: 'Strong quarterly credit growth & trend continuation signal confirmed across 20-day & 50-day SMAs.' 
      }
    ],
    performance: perf1M,
    decisions: [
      'Market Regime Agent: Classified market as RISK ON TRENDING with 80% target equity deployment.',
      'News Intelligence Agent: Global macro tariff risks monitored; domestic earnings momentum remains positive.',
      'Technical & Fundamental Analyst: Reliance and ICICI Bank exhibit top-tier relative strength vs Nifty 50.',
      'Risk Manager Agent: Preserved 21.5% cash buffer (exceeding 15% policy floor) to absorb potential volatility spikes.',
      'Portfolio Manager Agent: Rebalanced IT sector weight down to 10.2% while expanding banking & energy allocation.'
    ],
    marketIntelligence: {
      headlineCount: 4,
      highRiskCount: 1,
      positiveCount: 2,
      items: [
        {
          title: 'RBI Monetary Policy stance maintains growth liquidity focus',
          source: 'Economic Times',
          publishedAt: new Date().toISOString(),
          category: 'monetary_policy',
          symbols: ['HDFCBANK.NS', 'ICICIBANK.NS'],
          impact: 'POSITIVE',
          summary: 'Steady rate outlook supports banking net interest margins and credit growth.'
        },
        {
          title: 'Global supply chain & commodity price fluctuation monitored',
          source: 'Bloomberg',
          publishedAt: new Date().toISOString(),
          category: 'global_macro',
          symbols: ['RELIANCE.NS'],
          impact: 'HIGH_RISK',
          summary: 'Risk agent enforces position sizing caps below 8% single stock ceiling.'
        },
        {
          title: 'Indian IT services contract renewals show steady pipeline',
          source: 'Reuters',
          publishedAt: new Date().toISOString(),
          category: 'earnings_update',
          symbols: ['INFY.NS', 'TCS.NS'],
          impact: 'NEUTRAL',
          summary: 'Selective accumulation favored on pullbacks with strict stop-loss rules.'
        }
      ]
    },
    investmentThesis: {
      summary: 'The AI Fund Manager targets risk-adjusted outperformance against Nifty 50 by combining high-conviction trend continuation in Indian mega-caps, automated risk caps, and dynamic liquidity management.',
      focus: ['Nifty 50 Relative Strength', 'Disciplined Cash Buffer (>15%)', 'Institutional Risk Control'],
      watchlist: ['RELIANCE.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'BHARTIARTL.NS', 'LT.NS']
    },
    riskProfile: {
      score: 72,
      posture: 'Balanced Growth',
      cashBuffer: 0.215,
      maxSingleStockWeight: 8,
      maxDailyDeployment: 25,
      notes: [
        'Macro Regime: Risk-On Trending with positive market breadth.',
        'Single stock exposure strictly capped at 8% per policy rules.',
        'Stop-loss monitoring active across all delivery holdings.'
      ]
    },
    marketOutlook: {
      summary: 'Constructive outlook for Indian equity benchmark (Nifty 50) led by banking, capital goods, and energy leaders. Risk budget remains disciplined.',
      drivers: ['Large-cap relative strength', 'Defensive cash reserve', 'Strong institutional inflows'],
      bias: 'Constructive & Trend-Following'
    }
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
    return 'Our AI loop is currently generating +0.76% Alpha over Nifty 50 (+2.48% vs +1.72% Nifty return) on our ₹1 Crore paper portfolio.';
  } else if (msg.includes('it') || msg.includes('infosys') || msg.includes('tcs')) {
    return 'We recently trimmed INFY.NS by 18 shares to manage tech sector exposure while maintaining TCS.NS on positive trend continuation.';
  } else {
    return `As Chief Investment Officer of AI Trader Agent, our goal is outperforming Nifty 50 with ₹1 Crore capital using disciplined trend-following, strict risk management, and delivery trades during NSE hours (09:15-15:30 IST).`;
  }
}
