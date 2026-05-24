import { create } from 'zustand';
import { DCFInput, DCFOutput, SavedValuation, DCFCompareResponse } from '@/types/dcf';
import api from '@/lib/api';

interface DCFState {
  inputs: DCFInput;
  result: DCFOutput | null;
  compareResult: DCFCompareResponse | null;
  history: SavedValuation[];
  isCalculating: boolean;
  isComparing: boolean;
  isSaving: boolean;
  setInputs: (inputs: DCFInput) => void;
  calculate: () => Promise<void>;
  compare: (inputA: DCFInput, inputB: DCFInput) => Promise<void>;
  saveValuation: () => Promise<void>;
  fetchHistory: () => Promise<void>;
  deleteValuation: (id: string) => Promise<void>;
  toggleShare: (id: string, is_public: boolean) => Promise<void>;
}

const initialInputs: DCFInput = {
  ticker: '',
  revenue: [0, 0, 0],
  ebit_margin: 0.18,
  tax_rate: 0.25,
  capex_pct: 0.08,
  nwc_change_pct: 0.02,
  wacc: 0.12,
  terminal_growth_rate: 0.04,
  projection_years: 5,
  shares_outstanding: 100,
  net_debt: 0,
};

export const useDCFStore = create<DCFState>((set, get) => ({
  inputs: initialInputs,
  result: null,
  compareResult: null,
  history: [],
  isCalculating: false,
  isComparing: false,
  isSaving: false,

  setInputs: (inputs) => set({ inputs }),

  calculate: async () => {
    set({ isCalculating: true });
    try {
      const response = await api.post('/dcf/calculate', get().inputs);
      set({ result: response.data });
    } finally {
      set({ isCalculating: false });
    }
  },

  compare: async (inputA, inputB) => {
    set({ isComparing: true });
    try {
      const response = await api.post('/dcf/compare', { input_a: inputA, input_b: inputB });
      set({ compareResult: response.data });
    } finally {
      set({ isComparing: false });
    }
  },

  saveValuation: async () => {
    const { inputs, result } = get();
    if (!result) return;

    set({ isSaving: true });
    try {
      await api.post('/dcf/save', {
        dcf_input: inputs,
        dcf_output: result,
      });
      await get().fetchHistory();
    } finally {
      set({ isSaving: false });
    }
  },

  fetchHistory: async () => {
    try {
      const response = await api.get('/dcf/history');
      set({ history: response.data });
    } catch (error) {
      console.error(error);
    }
  },

  deleteValuation: async (id: string) => {
    try {
      await api.delete(`/dcf/history/${id}`);
      set((state) => ({
        history: state.history.filter((v) => v.id !== id),
      }));
    } catch (error) {
      console.error(error);
      throw error;
    }
  },

  toggleShare: async (id: string, is_public: boolean) => {
    try {
      await api.post(`/dcf/history/${id}/share?is_public=${is_public}`);
      set((state) => ({
        history: state.history.map((v) => 
          v.id === id ? { ...v, is_public } : v
        ),
      }));
    } catch (error) {
      console.error(error);
      throw error;
    }
  },
}));
