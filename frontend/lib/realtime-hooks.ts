import { useEffect, useState, useCallback, useRef } from 'react';
import { createClient } from './supabase';
import { apiFetch } from './api';
import { useAuthStore } from './auth-store';
import { useToast } from '@/components/ui/Toast';

export function useRealtimePortfolio(portfolioId?: string) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuthStore();
  const { toast } = useToast();
  const supabase = createClient();
  
  const refreshTimer = useRef<NodeJS.Timeout | null>(null);
  const positionsRef = useRef<any[]>([]);

  const fetchOverview = useCallback(async () => {
    try {
      const endpoint = portfolioId 
        ? `/portfolio/overview?portfolio_id=${portfolioId}` 
        : '/portfolio/overview';
      const result = await apiFetch(endpoint);
      setData(result);
      positionsRef.current = result.positions || [];
      setError(null);
    } catch (err: any) {
      console.error("Realtime fetch error:", err);
      // Don't show toast on initial empty load if user is logging in
      if (user) {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }, [portfolioId, user]);

  const debouncedRefresh = useCallback(() => {
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
    refreshTimer.current = setTimeout(() => {
      fetchOverview();
    }, 300); // 300ms debounce
  }, [fetchOverview]);

  useEffect(() => {
    if (!user) return;

    fetchOverview();

    // Subscribe to all relevant tables
    const channel = supabase
      .channel(`portfolio_sync_${portfolioId || 'default'}_${user.id}`)
      // Portfolio changes
      .on('postgres_changes', { 
        event: '*', 
        schema: 'public', 
        table: 'portfolios',
        filter: `user_id=eq.${user.id}`
      }, (payload) => {
        console.log('Live: Portfolio update', payload.eventType);
        debouncedRefresh();
      })
      // Position changes
      .on('postgres_changes', { 
        event: '*', 
        schema: 'public', 
        table: 'portfolio_positions'
      }, (payload) => {
        // Note: filtered in JS because portfolio_id check is needed
        const pid = (payload.new as any)?.portfolio_id || (payload.old as any)?.portfolio_id;
        if (portfolioId && pid !== portfolioId) return;
        console.log('Live: Position update', payload.eventType);
        debouncedRefresh();
      })
      // Transaction changes
      .on('postgres_changes', { 
        event: '*', 
        schema: 'public', 
        table: 'transactions',
        filter: `user_id=eq.${user.id}`
      }, (payload) => {
        console.log('Live: Transaction update', payload.eventType);
        debouncedRefresh();
      })
      // Historical Equity changes
      .on('postgres_changes', { 
        event: 'INSERT', 
        schema: 'public', 
        table: 'historical_equity',
        filter: `user_id=eq.${user.id}`
      }, () => {
        debouncedRefresh();
      })
      // Market Cache (Prices)
      .on('postgres_changes', { 
        event: 'UPDATE', 
        schema: 'public', 
        table: 'market_cache'
      }, (payload) => {
        const ticker = (payload.new as any)?.symbol;
        const isHolding = positionsRef.current.some(p => p.ticker === ticker);
        if (isHolding) {
           debouncedRefresh();
        }
      })
      .subscribe((status) => {
        if (status === 'CHANNEL_ERROR') {
          console.error('Realtime subscription error');
        }
      });

    return () => {
      if (refreshTimer.current) clearTimeout(refreshTimer.current);
      supabase.removeChannel(channel);
    };
  }, [user, portfolioId, debouncedRefresh]);

  return { data, loading, error, refresh: fetchOverview };
}
