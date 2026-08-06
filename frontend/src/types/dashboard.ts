export type DashboardData = {
  portfolio: {
    totalValue: number;
    cash: number;
    investedValue: number;
    dailyPnl: number;
    totalReturn: number;
    benchmarkReturn: number;
    alpha: number;
    marketRegime: string;
  };
  scheduler: {
    status: string;
    lastRun: string;
    nextMarketOpen: string;
    tradingWindow: string;
  };
  holdings: Array<{ symbol: string; name: string; weight: number; pnl: number; risk: string; conviction: number }>;
  trades: Array<{ time: string; symbol: string; side: string; quantity: number; price: number; reason: string }>;
  performance: Array<{ date: string; portfolio: number; benchmark: number }>;
  decisions: string[];
  marketIntelligence?: {
    headlineCount: number;
    highRiskCount: number;
    positiveCount: number;
    items: Array<{
      title: string;
      source: string;
      publishedAt: string;
      category: string;
      symbols: string[];
      impact: string;
      summary: string;
    }>;
  };
  investmentThesis?: {
    summary: string;
    focus: string[];
    watchlist: string[];
  };
  riskProfile?: {
    score: number;
    posture: string;
    cashBuffer: number;
    maxSingleStockWeight: number;
    maxDailyDeployment: number;
    notes: string[];
  };
  marketOutlook?: {
    summary: string;
    drivers: string[];
    bias: string;
  };
};
