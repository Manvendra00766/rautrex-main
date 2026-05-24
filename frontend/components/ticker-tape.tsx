"use client"

import { useEffect, useState, useMemo } from "react"
import { motion } from "framer-motion"

import { apiFetch } from "@/lib/api"
import { useRealtimePrices } from "@/lib/realtime-prices"

interface TapeItem {
  name: string
  ticker: string
  value: number
  change_percent: number
}

export default function TickerTape() {
  const [items, setItems] = useState<TapeItem[]>([])
  
  const tickers = useMemo(() => items.map(i => i.ticker), [items])
  const livePrices = useRealtimePrices(tickers)

  useEffect(() => {
    let isMounted = true

    const load = async () => {
      try {
        const data = await apiFetch("/market/indices")
        if (isMounted) {
          setItems(data.indices || [])
        }
      } catch {
        if (isMounted) {
          setItems([])
        }
      }
    }

    load()
    return () => { isMounted = false }
  }, [])

  const displayItems = useMemo(() => {
    return items.map(item => ({
      ...item,
      value: livePrices[item.ticker]?.value ?? item.value,
      change_percent: livePrices[item.ticker]?.change ?? item.change_percent
    }))
  }, [items, livePrices])

  if (displayItems.length === 0) {
    return (
      <div className="w-full bg-[var(--bg-surface)] rounded-sm py-2 px-4 border border-[var(--border)]">
        <div className="text-[10px] uppercase tracking-[0.2em] text-[var(--text-muted)] font-bold">Loading market tape...</div>
      </div>
    )
  }

  return (
    <div className="w-full overflow-hidden bg-[var(--bg-surface)] rounded-sm py-2 flex items-center border border-[var(--border)]">
      <motion.div
        animate={{ x: [0, -1000] }}
        transition={{ repeat: Infinity, duration: 28, ease: "linear" }}
        className="flex gap-12 whitespace-nowrap px-4"
      >
        {[...displayItems, ...displayItems].map((item, index) => (
          <div key={`${item.ticker}-${index}`} className="flex gap-3 items-center font-mono text-sm">
            <span className="font-bold text-[var(--text-primary)]">{item.ticker}</span>
            <span className="text-[var(--text-secondary)]">{(item.value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
            <span className={(item.change_percent ?? 0) >= 0 ? "text-[var(--positive)] font-bold" : "text-[var(--negative)] font-bold"}>
              {(item.change_percent ?? 0) >= 0 ? "+" : ""}
              {(item.change_percent ?? 0).toFixed(2)}%
            </span>
          </div>
        ))}
      </motion.div>
    </div>
  )
}
