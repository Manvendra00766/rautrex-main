export type ScreenerMetric =
  | "pe_ratio"
  | "pb_ratio"
  | "rsi_14"
  | "eps_growth_yoy"
  | "revenue_growth_yoy"
  | "market_cap_cr"
  | "week_52_from_high_pct";

export type ScreenerOperator = "lt" | "gt" | "lte" | "gte";

export interface ScreenerFilter {
  metric: ScreenerMetric;
  operator: ScreenerOperator;
  value: number;
}

export interface ScreenerRequest {
  filters: ScreenerFilter[];
  universe: "nifty50" | "nifty100";
  limit?: number;
}

export interface ScreenerResult {
  ticker: string;
  company_name: string;
  pe_ratio: number | null;
  pb_ratio: number | null;
  rsi_14: number | null;
  eps_growth_yoy: number | null;
  revenue_growth_yoy: number | null;
  market_cap_cr: number | null;
  week_52_from_high_pct: number | null;
  current_price: number | null;
}

export interface ScreenerPreset {
  id: string;
  name: string;
  filters: ScreenerFilter[];
  user_id: string;
  created_at?: string;
}
