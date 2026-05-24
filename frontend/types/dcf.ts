export interface DCFInput {
  ticker: string;
  revenue: number[];
  ebit_margin: number;
  tax_rate: number;
  capex_pct: number;
  da_pct: number;
  nwc_change_pct: number;
  wacc: number;
  terminal_growth_rate: number;
  projection_years: number;
  shares_outstanding: number;
  net_debt: number;
  currency?: string;
  unit?: string;
  unit_label?: string;
  exchange?: string;
  warnings?: string[];
  field_sources?: Record<string, string>;
}

export interface DCFOutput {
  ticker: string;
  intrinsic_value_per_share: number;
  current_market_price: number | null;
  upside_downside_pct: number | null;
  projected_fcfs: number[];
  terminal_value: number;
  enterprise_value: number;
  equity_value: number;
  wacc_used: number;
  sensitivity_table: Record<string, Record<string, number>>;
  valuation_date: string;
  warnings: string[];
  errors: string[];
  data_quality_score: string;
  field_sources: Record<string, string>;
  currency: string;
  unit: string;
  unit_label: string;
  exchange: string;
  market_price_native: number;
}
export interface SavedValuation {
  id: string;
  ticker: string;
  is_public: boolean;
  input_data: DCFInput;
  output_data: DCFOutput;
  created_at: string;
}

export interface DCFCompareResponse {
  winner: string;
  upside_difference_pct: number;
  output_a: DCFOutput;
  output_b: DCFOutput;
}
