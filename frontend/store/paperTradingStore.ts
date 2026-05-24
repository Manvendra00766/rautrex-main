import { create } from 'zustand';
import { apiFetch } from '@/lib/api';
import { Portfolio, Order, PlaceOrderRequest } from '@/types/paper_trading';

interface PaperTradingState {
  portfolio: Portfolio | null;
  orders: Order[];
  isLoading: boolean;
  isPlacingOrder: boolean;
  fetchPortfolio: () => Promise<void>;
  fetchOrders: () => Promise<void>;
  placeOrder: (req: PlaceOrderRequest) => Promise<Order>;
  resetAccount: () => Promise<void>;
}

export const usePaperTradingStore = create<PaperTradingState>((set, get) => ({
  portfolio: null,
  orders: [],
  isLoading: false,
  isPlacingOrder: false,

  fetchPortfolio: async () => {
    set({ isLoading: true });
    try {
      const data = await apiFetch('/paper/portfolio');
      set({ portfolio: data });
    } catch (error) {
      console.error('Failed to fetch paper portfolio:', error);
      throw error;
    } finally {
      set({ isLoading: false });
    }
  },

  fetchOrders: async () => {
    try {
      const data = await apiFetch('/paper/orders');
      set({ orders: data });
    } catch (error) {
      console.error('Failed to fetch paper orders:', error);
      throw error;
    }
  },

  placeOrder: async (req: PlaceOrderRequest) => {
    set({ isPlacingOrder: true });
    try {
      const order = await apiFetch('/paper/order', {
        method: 'POST',
        body: JSON.stringify(req),
      });
      await get().fetchPortfolio();
      await get().fetchOrders();
      return order;
    } catch (error) {
      console.error('Failed to place order:', error);
      throw error;
    } finally {
      set({ isPlacingOrder: false });
    }
  },

  resetAccount: async () => {
    set({ isLoading: true });
    try {
      await apiFetch('/paper/reset', { method: 'POST' });
      await get().fetchPortfolio();
      await get().fetchOrders();
    } catch (error) {
      console.error('Failed to reset account:', error);
      throw error;
    } finally {
      set({ isLoading: false });
    }
  },
}));
