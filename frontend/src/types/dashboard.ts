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
    startingCapital?: number;
    inceptionDate?: string | null;
    tradeCount?: number;
    buyCount?: number;
    sellCount?: number;
    cashUtilizationPct?: number;
    deploymentPct?: number;
    openPositions?: number;
    universeSize?: number;
  };
  comparison?: {
    inceptionDate: string | null;
    startingCapital: number;
    agentValue: number;
    agentReturnPct: number;
    agentProfit: number;
    niftyValue: number;
    niftyReturnPct: number;
    niftyProfit: number;
    alphaPct: number;
  };
  scheduler: {
    status: string;
    lastRun: string;
    nextMarketOpen: string;
    tradingWindow: string;
    lastAgentCycle?: string | null;
    lastMarketDataAt?: string | null;
    lastNewsAt?: string | null;
    lastEngineProvider?: string;
    lastEngineNote?: string;
  };
  holdings: Array<{ symbol: string; name: string; sector?: string; weight: number; pnl: number; risk: string; conviction: number }>;
  trades: Array<{ time: string; symbol: string; side: string; quantity: number; price: number; reason: string; status?: string; provider?: string }>;
  performance: Array<{ date: string; portfolioValue: number; benchmarkValue: number; portfolioReturn: number; benchmarkReturn: number }>;
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
  publicSignals?: {
    fundamentals: Array<{
      symbol: string;
      name: string;
      marketCap?: number | null;
      trailingPE?: number | null;
      forwardPE?: number | null;
      priceToBook?: number | null;
      profitMargins?: number | null;
      revenueGrowth?: number | null;
      debtToEquity?: number | null;
      freeCashflow?: number | null;
      earningsGrowth?: number | null;
    }>;
    headlines: Array<{
      title: string;
      source: string;
      published_at: string;
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
  dataStatus?: {
    source: string;
    updatedAt: string | null;
    message: string;
    persistence: string;
  };
  research?: {
    daily: { text: string; provider: string; generatedAt: string } | null;
    monthly: { text: string; provider: string; generatedAt: string } | null;
  };
  isFallback?: boolean;
};
