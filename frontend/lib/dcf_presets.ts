import { DCFInput } from "@/types/dcf";

export type PresetKey = "Conservative" | "Base" | "Aggressive";

export interface Preset {
  label: string;
  description: string;
  color: "yellow" | "blue" | "green";
  values: Partial<DCFInput>;
}

export const PRESETS: Record<PresetKey, Preset> = {
  Conservative: {
    label: "Conservative",
    description: "Assumes higher discount rates and cautious margins for a margin-of-safety valuation.",
    color: "yellow",
    values: {
      ebit_margin: 0.14,
      tax_rate: 0.28,
      capex_pct: 0.10,
      nwc_change_pct: 0.03,
      wacc: 0.14,
      terminal_growth_rate: 0.03,
      projection_years: 5,
    },
  },
  Base: {
    label: "Base",
    description: "Balanced historical performance projections aligned with typical market expectations.",
    color: "blue",
    values: {
      ebit_margin: 0.18,
      tax_rate: 0.25,
      capex_pct: 0.08,
      nwc_change_pct: 0.02,
      wacc: 0.12,
      terminal_growth_rate: 0.04,
      projection_years: 5,
    },
  },
  Aggressive: {
    label: "Aggressive",
    description: "High-growth scenario with optimized margins and lower capital costs.",
    color: "green",
    values: {
      ebit_margin: 0.24,
      tax_rate: 0.22,
      capex_pct: 0.06,
      nwc_change_pct: 0.01,
      wacc: 0.10,
      terminal_growth_rate: 0.05,
      projection_years: 7,
    },
  },
};
