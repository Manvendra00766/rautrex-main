import { create } from 'zustand';
import api from '@/lib/api';
import { formatError } from '@/lib/utils';

export interface PriceAlert {
  id: string;
  user_id: string;
  ticker: string;
  condition: 'above' | 'below';
  target_price: number;
  is_triggered: boolean;
  created_at: string;
  triggered_at: string | null;
}

interface AlertFilters {
  ticker: string;
  condition: 'above' | 'below';
  target_price: number;
}

interface AlertsState {
  alerts: PriceAlert[];
  loading: boolean;
  error: string | null;
  fetchAlerts: () => Promise<void>;
  createAlert: (alert: AlertFilters) => Promise<void>;
  deleteAlert: (id: string) => Promise<void>;
  updateAlertTriggered: (symbol: string, target_price: number) => void;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const useAlertsStore = create<AlertsState>((set, get) => ({
  alerts: [],
  loading: false,
  error: null,

  fetchAlerts: async () => {
    set({ loading: true, error: null });
    try {
      const response = await api.get('/alerts/');
      set({ alerts: response.data, loading: false });
    } catch (err: any) {
      set({ error: formatError(err), loading: false });
    }
  },

  createAlert: async (alertData) => {
    set({ loading: true, error: null });
    try {
      await api.post('/alerts/', alertData);
      get().fetchAlerts();
    } catch (err: any) {
      set({ error: formatError(err), loading: false });
    }
  },

  deleteAlert: async (id) => {
    set({ loading: true, error: null });
    try {
      await api.delete(`/alerts/${id}`);
      set((state) => ({
        alerts: state.alerts.filter((a) => a.id !== id),
        loading: false,
      }));
    } catch (err: any) {
      set({ error: formatError(err), loading: false });
    }
  },

  updateAlertTriggered: (symbol, targetPrice) => {
    set((state) => ({
      alerts: state.alerts.map((a) => 
        a.ticker.toUpperCase() === symbol.toUpperCase() && a.target_price === targetPrice
          ? { ...a, is_triggered: true, triggered_at: new Date().toISOString() }
          : a
      ),
    }));
  },
}));
