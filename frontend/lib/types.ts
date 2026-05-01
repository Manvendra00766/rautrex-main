export interface PortfolioRecord {
  id: string
  name: string
  strategy?: string | null
  cash_balance?: number
  description?: string | null
  base_currency?: string
  benchmark_symbol?: string
  is_default?: boolean
}

export interface PortfolioPosition {
  ticker: string
  name: string
  asset_type: string
  currency: string
  exchange?: string | null
  sector?: string | null
  country?: string | null
  shares: number
  avg_cost_per_share: number
  live_price: number
  previous_close: number
  cost_basis: number
  market_value: number
  unrealized_pnl: number
  realized_pnl: number
  daily_pnl: number
  total_return_pct: number
  weight_pct: number
  daily_return_pct: number
  change_percent: number
}

export interface EquityPoint {
  snapshot_date: string
  nav: number
  cash_balance: number
  market_value: number
  daily_pnl: number
}

export interface AllocationBucket {
  label: string
  value: number
  weight_pct: number
}

export interface PortfolioSummary {
  nav: number
  cash: number
  buying_power: number
  holdings_market_value: number
  holdings_count: number
  daily_pnl: number
  daily_return_pct: number
  mtd_return_pct: number
  ytd_return_pct: number
  gross_exposure: number
  gross_exposure_pct: number
  net_exposure: number
  net_exposure_pct: number
  volatility_annualized: number
  sharpe_ratio: number
  sortino_ratio: number
  max_drawdown: number
  var_95: number
  beta_vs_spy: number
  top_position_pct: number
  herfindahl_index: number
  realized_pnl?: number
  realized_pnl_total?: number
  unrealized_pnl: number
}

export interface PortfolioOverview {
  portfolio: PortfolioRecord | null
  summary: PortfolioSummary | null
  positions: PortfolioPosition[]
  equity_curve: EquityPoint[]
  allocation: {
    by_sector: AllocationBucket[]
    by_asset_type: AllocationBucket[]
    by_country: AllocationBucket[]
  }
  warnings: Array<{
    level: string
    code: string
    message: string
  }>
  transactions_count?: number
  last_priced_at?: string | null
}
