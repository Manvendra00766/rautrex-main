export interface Position {
  ticker: string;
  shares: number;
  avg_cost_per_share: number;
  live_price: number;
  market_value: number;
  unrealized_pnl: number;
  daily_pnl: number;
  total_return_pct: number;
  weight_pct: number;
  asset_type: string;
  sector: string;
}

export interface Summary {
  nav: number;
  daily_pnl: number;
  daily_return_pct: number;
  mtd_return_pct: number;
  ytd_return_pct: number;
  cash: number;
  gross_exposure: number;
  gross_exposure_pct: number;
  net_exposure: number;
  net_exposure_pct: number;
  var_95: number;
  sharpe_ratio: number;
  max_drawdown: number;
  holdings_count: number;
}

export interface SandboxData {
  portfolio: {
    id: string;
    name: string;
    is_default: boolean;
  };
  summary: Summary;
  positions: Position[];
  equity_curve: { snapshot_date: string; nav: number }[];
  allocation: {
    by_sector: { label: string; weight_pct: number }[];
    by_asset_type: { label: string; weight_pct: number }[];
    by_country: { label: string; weight_pct: number }[];
  };
  alerts: {
    id: string;
    severity: string;
    title: string;
    message: string;
    affected_asset: string;
    triggered_at: string;
  }[];
  warnings: { code: string; message: string }[];
  monteCarlo: {
    simulations: number;
    medianReturnPct: number;
    varPct: number;
  };
}

export const sandboxData: SandboxData = {
  portfolio: {
    id: "sandbox-portfolio",
    name: "Sandbox Tactical Alpha",
    is_default: true,
  },
  summary: {
    nav: 125000,
    daily_pnl: 675,
    daily_return_pct: 0.54,
    mtd_return_pct: 3.45,
    ytd_return_pct: 14.82,
    cash: 14000,
    gross_exposure: 111000,
    gross_exposure_pct: 88.8,
    net_exposure: 111000,
    net_exposure_pct: 88.8,
    var_95: 0.021, // 2.1%
    sharpe_ratio: 2.15,
    max_drawdown: 0.045, // 4.5%
    holdings_count: 4,
  },
  positions: [
    {
      ticker: "AAPL",
      shares: 150,
      avg_cost_per_share: 152.03,
      live_price: 180.00,
      market_value: 27000,
      unrealized_pnl: 4195.5,
      daily_pnl: 120.0,
      total_return_pct: 18.4,
      weight_pct: 21.6,
      asset_type: "Equity",
      sector: "Technology",
    },
    {
      ticker: "NVDA",
      shares: 40,
      avg_cost_per_share: 670.64,
      live_price: 900.00,
      market_value: 36000,
      unrealized_pnl: 9174.4,
      daily_pnl: 450.0,
      total_return_pct: 34.2,
      weight_pct: 28.8,
      asset_type: "Equity",
      sector: "Technology",
    },
    {
      ticker: "TSLA",
      shares: 60,
      avg_cost_per_share: 184.98,
      live_price: 170.00,
      market_value: 10200,
      unrealized_pnl: -898.8,
      daily_pnl: -75.0,
      total_return_pct: -8.1,
      weight_pct: 8.16,
      asset_type: "Equity",
      sector: "Automotive",
    },
    {
      ticker: "MSFT",
      shares: 90,
      avg_cost_per_share: 372.67,
      live_price: 420.00,
      market_value: 37800,
      unrealized_pnl: 4259.7,
      daily_pnl: 180.0,
      total_return_pct: 12.7,
      weight_pct: 30.24,
      asset_type: "Equity",
      sector: "Technology",
    },
  ],
  equity_curve: [
    { snapshot_date: "24-Apr", nav: 112000 },
    { snapshot_date: "27-Apr", nav: 113500 },
    { snapshot_date: "28-Apr", nav: 114000 },
    { snapshot_date: "29-Apr", nav: 113000 },
    { snapshot_date: "30-Apr", nav: 115000 },
    { snapshot_date: "01-May", nav: 116200 },
    { snapshot_date: "04-May", nav: 115900 },
    { snapshot_date: "05-May", nav: 117000 },
    { snapshot_date: "06-May", nav: 118400 },
    { snapshot_date: "07-May", nav: 117800 },
    { snapshot_date: "08-May", nav: 119500 },
    { snapshot_date: "11-May", nav: 120200 },
    { snapshot_date: "12-May", nav: 119800 },
    { snapshot_date: "13-May", nav: 121500 },
    { snapshot_date: "14-May", nav: 122400 },
    { snapshot_date: "15-May", nav: 121900 },
    { snapshot_date: "18-May", nav: 122800 },
    { snapshot_date: "19-May", nav: 123400 },
    { snapshot_date: "20-May", nav: 124100 },
    { snapshot_date: "21-May", nav: 123800 },
    { snapshot_date: "22-May", nav: 125000 },
  ],
  allocation: {
    by_sector: [
      { label: "Technology", weight_pct: 80.64 },
      { label: "Automotive", weight_pct: 8.16 },
    ],
    by_asset_type: [
      { label: "Equity", weight_pct: 88.8 },
    ],
    by_country: [
      { label: "United States", weight_pct: 88.8 },
    ],
  },
  alerts: [
    {
      id: "alert-1",
      severity: "warning",
      title: "AI ML Signal Alert: AAPL BUY",
      message: "AAPL ensemble neural network indicates BUY signal with 87% confidence.",
      affected_asset: "AAPL",
      triggered_at: new Date().toISOString(),
    },
    {
      id: "alert-2",
      severity: "info",
      title: "AI ML Signal Alert: GOOGL HOLD",
      message: "GOOGL model analysis indicates HOLD with 72% confidence.",
      affected_asset: "GOOGL",
      triggered_at: new Date().toISOString(),
    },
    {
      id: "alert-3",
      severity: "critical",
      title: "AI ML Signal Alert: AMZN SELL",
      message: "AMZN sentiment and technical indicator ensemble triggers SELL signal with 64% confidence.",
      affected_asset: "AMZN",
      triggered_at: new Date().toISOString(),
    }
  ],
  warnings: [],
  monteCarlo: {
    simulations: 10000,
    medianReturnPct: 22.3,
    varPct: 2.1,
  },
};
