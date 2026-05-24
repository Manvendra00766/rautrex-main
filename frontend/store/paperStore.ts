import { create } from 'zustand';
import { 
  Portfolio, 
  Order, 
  PlaceOrderRequest 
} from '@/types/paper';
import { apiFetch } from '@/lib/api';

interface PaperTradingState {
  portfolio: Portfolio | null;
  orders: Order[];
  isLoading: boolean;
  isPlacingOrder: boolean;
  
  // Actions
  fetchPortfolio: () => Promise<void>;
  fetchOrders: () => Promise<void>;
  placeOrder: (req: PlaceOrderRequest) => Promise<Order | null>;
  resetAccount: () => Promise<void>;
}

export const usePaperStore = create<PaperTradingState>((set, get) => ({
  portfolio: null,
  orders: [],
  isLoading: false,
  isPlacingOrder: false,

  fetchPortfolio: async () => {
    set({ isLoading: true });
    try {
      const portfolio = await apiFetch('/paper/portfolio');
      set({ portfolio });
    } catch (error) {
      console.error('Failed to fetch portfolio:', error);
    } finally {
      set({ isLoading: false });
    }
  },

  fetchOrders: async () => {
    try {
      const orders = await apiFetch('/paper/orders');
      set({ orders });
    } catch (error) {
      console.error('Failed to fetch orders:', error);
    }
  },

  placeOrder: async (req) => {
    set({ isPlacingOrder: true });
    try {
      const order = await apiFetch('/paper/order', {
        method: 'POST',
        body: JSON.stringify(req)
      });
      
      // Refresh portfolio and orders
      await get().fetchPortfolio();
      await get().fetchOrders();
      
      return order;
    } catch (error) {
      console.error('Order failed:', error);
      return null;
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
      console.error('Reset failed:', error);
    } finally {
      set({ isLoading: false });
    }
  }
}));
