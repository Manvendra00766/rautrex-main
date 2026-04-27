import { create } from 'zustand'

interface MarketState {
  activeTicker: string
  setActiveTicker: (ticker: string) => void
}

export const useMarketStore = create<MarketState>((set) => ({
  activeTicker: 'AAPL',
  setActiveTicker: (ticker) => set({ activeTicker: ticker }),
}))
