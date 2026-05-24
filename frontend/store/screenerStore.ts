import { create } from 'zustand';
import api from '@/lib/api';
import { formatError } from '@/lib/utils';

interface ScreenerFilters {
  min_pe?: number;
  max_pe?: number;
  min_roe?: number;
  max_roe?: number;
  min_rsi?: number;
  max_rsi?: number;
  min_market_cap?: number;
  max_market_cap?: number;
  min_dcf_margin_of_safety?: number;
}

interface StockResult {
  symbol: string;
  company_name: string;
  current_price: number | null;
  pe_ratio: number | null;
  roe: number | null;
  rsi: number | null;
  market_cap: number | null;
  dcf_margin_of_safety: number | null;
  signal: 'BUY' | 'HOLD' | 'AVOID';
}

interface ScreenerState {
  filters: ScreenerFilters;
  results: StockResult[];
  loading: boolean;
  error: string | null;
  cacheStatus: string | null;
  setFilter: (key: keyof ScreenerFilters, value: number | undefined) => void;
  runScreener: () => Promise<void>;
  resetFilters: () => void;
  clearCache: () => Promise<void>;
}

const DEFAULT_FILTERS: ScreenerFilters = {
  min_pe: 5,
  max_pe: 40,
  min_roe: 10,
  min_rsi: 30,
  max_rsi: 70,
  min_market_cap: 10000,
  min_dcf_margin_of_safety: 0
};

export const useScreenerStore = create<ScreenerState>((set, get) => ({
  filters: DEFAULT_FILTERS,
  results: [],
  loading: false,
  error: null,
  cacheStatus: null,

  setFilter: (key, value) => {
    set((state) => ({
      filters: { ...state.filters, [key]: value },
    }));
  },

  resetFilters: () => set({ filters: DEFAULT_FILTERS, results: [] }),

  runScreener: async () => {
    set({ loading: true, error: null });
    try {
      const response = await api.post('/screener/filter', get().filters);
      // Backend now returns { results, status, ... }
      const data = response.data;
      set({ 
        results: data.results || [], 
        cacheStatus: data.status || null,
        loading: false 
      });
    } catch (err: any) {
      set({ 
        error: formatError(err), 
        loading: false 
      });
    }
  },

  clearCache: async () => {
    try {
      await api.delete('/screener/cache');
      await get().runScreener();
    } catch (err) {
      console.error("Failed to clear cache", err);
    }
  }
}));
