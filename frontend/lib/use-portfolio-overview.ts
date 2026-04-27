"use client"

import { startTransition, useCallback, useEffect, useState, useRef } from "react"

import { apiFetch } from "@/lib/api"
import type { PortfolioOverview, PortfolioRecord } from "@/lib/types"
import { createClient } from "./supabase"
import { useAuthStore } from "./auth-store"

interface UsePortfolioOverviewState {
  portfolios: PortfolioRecord[]
  overview: PortfolioOverview | null
  loading: boolean
  error: string | null
  selectedPortfolioId: string | null
  setSelectedPortfolioId: (portfolioId: string) => void
  refresh: () => Promise<void>
}

export function usePortfolioOverview(): UsePortfolioOverviewState {
  const [portfolios, setPortfolios] = useState<PortfolioRecord[]>([])
  const [overview, setOverview] = useState<PortfolioOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedPortfolioId, setSelectedPortfolioIdState] = useState<string | null>(null)
  
  const { user } = useAuthStore()
  const supabase = createClient()
  const refreshTimer = useRef<NodeJS.Timeout | null>(null)
  const positionsRef = useRef<any[]>([])

  const fetchOverview = useCallback(async (isSilent = false) => {
    if (!isSilent) setLoading(true)
    setError(null)
    try {
      const portfolioList = await apiFetch("/users/me/portfolios")
      const normalizedPortfolios: PortfolioRecord[] = portfolioList || []
      setPortfolios(normalizedPortfolios)

      const effectivePortfolioId =
        selectedPortfolioId ||
        normalizedPortfolios.find((portfolio) => portfolio.is_default)?.id ||
        normalizedPortfolios[0]?.id ||
        null

      if (!effectivePortfolioId) {
        setOverview({
          portfolio: null,
          summary: null,
          positions: [],
          equity_curve: [],
          allocation: { by_sector: [], by_asset_type: [], by_country: [] },
          warnings: [],
        })
        setLoading(false)
        return
      }

      const data = await apiFetch(`/portfolio/overview?portfolio_id=${effectivePortfolioId}`)
      setOverview(data)
      positionsRef.current = data.positions || []
      if (effectivePortfolioId !== selectedPortfolioId) {
        setSelectedPortfolioIdState(effectivePortfolioId)
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load portfolio overview")
    } finally {
      setLoading(false)
    }
  }, [selectedPortfolioId])

  const debouncedRefresh = useCallback(() => {
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
    refreshTimer.current = setTimeout(() => {
      fetchOverview(true); // Silent refresh to avoid flashing spinners
    }, 400); 
  }, [fetchOverview]);

  // Handle manual/initial load and portfolio switching
  useEffect(() => {
    fetchOverview()
  }, [selectedPortfolioId])

  // Realtime Subscriptions
  useEffect(() => {
    if (!user) return;

    const channel = supabase
      .channel(`rt_portfolio_sync_${user.id}`)
      .on('postgres_changes', { 
        event: '*', 
        schema: 'public', 
        table: 'portfolios', 
        filter: `user_id=eq.${user.id}` 
      }, (payload) => {
        console.debug('Realtime: Portfolio change', payload.eventType);
        debouncedRefresh();
      })
      .on('postgres_changes', { 
        event: '*', 
        schema: 'public', 
        table: 'portfolio_positions' 
      }, (payload) => {
        // Filter for our selected portfolio in JS
        const pid = (payload.new as any)?.portfolio_id || (payload.old as any)?.portfolio_id;
        if (selectedPortfolioId && pid === selectedPortfolioId) {
          console.debug('Realtime: Position change', payload.eventType);
          debouncedRefresh();
        }
      })
      .on('postgres_changes', { 
        event: '*', 
        schema: 'public', 
        table: 'transactions', 
        filter: `user_id=eq.${user.id}` 
      }, (payload) => {
        console.debug('Realtime: Transaction change', payload.eventType);
        debouncedRefresh();
      })
      .on('postgres_changes', { 
        event: 'INSERT', 
        schema: 'public', 
        table: 'historical_equity', 
        filter: `user_id=eq.${user.id}` 
      }, () => {
        debouncedRefresh();
      })
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
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
      if (refreshTimer.current) clearTimeout(refreshTimer.current);
    };
  }, [user, selectedPortfolioId, debouncedRefresh]);

  const setSelectedPortfolioId = useCallback((portfolioId: string) => {
    startTransition(() => {
      setSelectedPortfolioIdState(portfolioId)
    })
  }, [])

  return {
    portfolios,
    overview,
    loading,
    error,
    selectedPortfolioId,
    setSelectedPortfolioId,
    refresh: () => fetchOverview(false),
  }
}
