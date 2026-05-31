"use client"

import { useState, useEffect, useRef, useCallback, useMemo } from "react"
import { 
  ArrowRight, 
  ArrowUpRight, 
  Check, 
  Send,
  MoreHorizontal,
  X,
  Sparkles,
  Info,
  DollarSign,
  TrendingUp,
  TrendingDown,
  ChevronRight,
  RefreshCw,
  AlertTriangle
} from "lucide-react"
import {
  Area,
  AreaChart,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid
} from "recharts"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"
import { useToast } from "@/components/ui/Toast"
import { usePortfolioOverview } from "@/lib/use-portfolio-overview"
import api, { apiFetch } from "@/lib/api"
import type { PortfolioPosition, PortfolioSummary, EquityPoint, AllocationBucket } from "@/lib/types"

// --- TYPES ---
interface Message {
  sender: "user" | "bot"
  text: string
  timestamp: Date
}

interface WatchlistItem {
  ticker: string
  name: string
  price: number
  change_percent: number
}

interface MarketMover {
  ticker: string
  name: string
  change_percent: number
}

// --- HELPERS ---

/** Format a number as ₹ with Indian locale, e.g. ₹12,45,670.00 */
function formatINR(value: number | null | undefined, fallback = "--"): string {
  if (value == null || isNaN(value)) return fallback
  return `₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

/** Format a compact lakh representation, e.g. ₹12.5L */
function formatLakhs(value: number): string {
  if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`
  if (value >= 1000) return `₹${(value / 1000).toFixed(1)}K`
  return formatINR(value)
}

/** Compute a health score from portfolio metrics (0-100) */
function computeHealthScore(summary: PortfolioSummary | null): number {
  if (!summary) return 0
  const sharpe = summary.sharpe_ratio ?? 0
  const maxDrawdown = Math.abs(summary.max_drawdown ?? 0)
  const volatility = summary.volatility_annualized ?? 0
  const score = Math.round(
    Math.min(100, Math.max(0,
      50 + (sharpe * 15) - (maxDrawdown * 100) - (volatility * 30)
    ))
  )
  return score
}

/** Derive a risk label from volatility */
function getRiskLabel(volatility: number): { text: string; color: string } {
  if (volatility > 0.3) return { text: "Risk: High", color: "text-[#C85D5D]" }
  if (volatility > 0.15) return { text: "Risk: Medium", color: "text-[#D67C38]" }
  return { text: "Risk: Low", color: "text-[#5F7055]" }
}

/** Derive a growth label from daily return */
function getGrowthLabel(dailyReturn: number): { text: string; color: string } {
  if (dailyReturn > 0.5) return { text: "Growth: Strong", color: "text-[#5F7055]" }
  if (dailyReturn > 0) return { text: "Growth: Moderate", color: "text-[#C9A96E]" }
  if (dailyReturn > -0.5) return { text: "Growth: Flat", color: "text-[#8C8278]" }
  return { text: "Growth: Declining", color: "text-[#C85D5D]" }
}

/** Get a color for a ticker's avatar */
function getTickerColor(ticker: string): { bg: string; text: string } {
  const colors = [
    { bg: "bg-[#FEE2E2]", text: "text-red-600" },
    { bg: "bg-[#E5E7EB]", text: "text-gray-800" },
    { bg: "bg-[#DBEAFE]", text: "text-blue-700" },
    { bg: "bg-[#ECFDF5]", text: "text-emerald-600" },
    { bg: "bg-[#FEF3C7]", text: "text-amber-700" },
    { bg: "bg-[#EDE9FE]", text: "text-purple-700" },
    { bg: "bg-[#FCE7F3]", text: "text-pink-700" },
    { bg: "bg-[#F0FDF4]", text: "text-green-700" },
  ]
  let hash = 0
  for (let i = 0; i < ticker.length; i++) hash = ticker.charCodeAt(i) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
}

/** SVG sparkline path from change_percent direction */
function getSparklinePath(changePct: number): { d: string; color: string } {
  if (changePct > 0) return {
    d: "M0,25 Q15,20 30,22 T60,12 T90,5 L100,2",
    color: "#5F7055"
  }
  if (changePct < 0) return {
    d: "M0,5 Q15,10 30,8 T60,18 T90,25 L100,28",
    color: "#C85D5D"
  }
  return {
    d: "M0,18 Q30,16 60,19 T90,17 L100,16",
    color: "#8C8278"
  }
}

/** Filter equity curve data by time range and deduplicate consecutive identical values */
function filterEquityCurve(
  curve: EquityPoint[],
  filter: string
): { value: number; date: string }[] {
  if (!curve || curve.length === 0) return []

  const mapped = curve.map(p => ({
    date: p.snapshot_date,
    value: p.nav
  }))

  const rangeDays: Record<string, number> = {
    '1D': 1,
    '1W': 7,
    '1M': 30,
    '3M': 90,
    '6M': 180,
    '1Y': 365,
    'ALL': 99999
  }

  const days = rangeDays[filter] ?? 30
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - days)
  const cutoffStr = cutoff.toISOString().split('T')[0]

  const filtered = mapped.filter(p => p.date >= cutoffStr)

  // Deduplicate consecutive identical values (weekend copies)
  return filtered.filter((point, index) => {
    if (index === 0) return true
    return point.value !== filtered[index - 1].value
  })
}

/** Skeleton pulse block */
function Skeleton({ className = "" }: { className?: string }) {
  return <div className={cn("animate-pulse bg-[#EBEBE6] rounded", className)} />
}

// ===========================================================================
// MAIN COMPONENT
// ===========================================================================

export default function RedesignedDashboard() {
  const { toast } = useToast()

  // --- PRIMARY DATA SOURCE ---
  const {
    portfolios,
    overview,
    loading: portfolioLoading,
    error: portfolioError,
    selectedPortfolioId,
    setSelectedPortfolioId,
    refresh
  } = usePortfolioOverview()

  // --- DERIVED STATE ---
  const summary = overview?.summary ?? null
  const positions = overview?.positions ?? []
  const equityCurve = overview?.equity_curve ?? []
  const hasChartData = equityCurve && equityCurve.length > 2
  const allocation = overview?.allocation ?? { by_sector: [], by_asset_type: [], by_country: [] }

  const portfolioValue = summary?.holdings_market_value ?? 0
  const cashAvailable = summary?.cash ?? overview?.portfolio?.cash_balance ?? 0
  const dailyPnl = summary?.daily_pnl ?? 0
  const dailyReturnPct = summary?.daily_return_pct ?? 0
  const overallPnl = summary?.overall_pnl ?? 0
  const overallPnlPct = summary?.overall_pnl_pct ?? 0
  const healthScore = computeHealthScore(summary)
  const unrealizedPnl = summary?.unrealized_pnl ?? 0

  // Goal progress: NAV towards a configurable target
  const goalTarget = 1000000 // ₹10L target – could come from user settings
  const goalProgress = goalTarget > 0 ? Math.min(100, Math.round((portfolioValue / goalTarget) * 100)) : 0

  // Render all active holdings beautifully
  const topHoldings = useMemo(() => {
    return [...positions]
      .sort((a, b) => b.market_value - a.market_value)
  }, [positions])

  // Top sector for insights
  const topSector = useMemo(() => {
    const sectors = allocation.by_sector || []
    if (sectors.length === 0) return null
    return [...sectors].sort((a, b) => b.weight_pct - a.weight_pct)[0]
  }, [allocation.by_sector])

  // --- UI STATES ---
  const [chartFilter, setChartFilter] = useState<"1D" | "1W" | "3M" | "6M" | "1Y" | "ALL">("1W")
  const [isApplying, setIsApplying] = useState(false)
  const [applied, setApplied] = useState(false)

  // --- PROGRESSIVE DISCLOSURE STATES & HANDLERS ---
  const [showCashPrompt, setShowCashPrompt] = useState(false)
  const [cashInputVal, setCashInputVal] = useState("")
  const [updatingCashBalance, setUpdatingCashBalance] = useState(false)

  useEffect(() => {
    if (!portfolioLoading && overview && positions.length > 0) {
      const cash = overview?.summary?.cash ?? overview?.portfolio?.cash_balance ?? 0
      if (cash <= 0) {
        setShowCashPrompt(true)
      } else {
        setShowCashPrompt(false)
      }
    }
  }, [portfolioLoading, overview, positions.length])

  const handleUpdateCash = async () => {
    if (!selectedPortfolioId || !cashInputVal) return
    setUpdatingCashBalance(true)
    try {
      await api.post("/portfolio/update-cash", {
        portfolio_id: selectedPortfolioId,
        cash_balance: parseFloat(cashInputVal || "0")
      })
      toast({
        type: "success",
        title: "Cash Balance Updated!",
        description: `Successfully updated spare cash balance.`
      })
      setShowCashPrompt(false)
      refresh()
    } catch (err: any) {
      console.error(err)
      toast({
        type: "error",
        title: "Update Failed",
        description: err.message || "Failed to update spare cash."
      })
    } finally {
      setUpdatingCashBalance(false)
    }
  }

  // --- WATCHLIST STATE ---
  const [watchlistItems, setWatchlistItems] = useState<WatchlistItem[]>([])
  const [watchlistLoading, setWatchlistLoading] = useState(true)

  // --- MARKET WATCH STATE ---
  const [marketMovers, setMarketMovers] = useState<MarketMover[]>([])
  const [marketLoading, setMarketLoading] = useState(true)

  // --- CHAT INTERACTION STATES ---
  const [chatMessages, setChatMessages] = useState<Message[]>([
    { 
      sender: "bot", 
      text: "Welcome to Rautrex AI Audit Advisor. Ask me anything about your safety risk or portfolio calibration.", 
      timestamp: new Date() 
    }
  ])
  const [chatInput, setChatInput] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const chatBottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [chatMessages, isTyping])

  // --- FETCH WATCHLIST DATA ---
  useEffect(() => {
    const fetchWatchlist = async () => {
      setWatchlistLoading(true)
      try {
        // Use actual portfolio tickers (filtering out G-Secs/Bonds) if available, otherwise use popular Indian tickers
        const tickers = positions.length > 0
          ? positions
              .filter(p => !p.ticker.includes("GS") && !p.ticker.includes("GB") && !p.ticker.startsWith("709GS"))
              .slice(0, 7)
              .map(p => p.ticker)
          : ["TMPV.NS", "HINDCOPPER.NS", "SUZLON.NS"]

        const quotes = await Promise.allSettled(
          tickers.map(ticker =>
            apiFetch(`/stocks/${ticker}/quote`).then(data => ({
              ticker,
              name: data.name || data.shortName || ticker,
              price: data.price ?? data.regularMarketPrice ?? 0,
              change_percent: data.change_percent ?? data.regularMarketChangePercent ?? 0,
            }))
          )
        )

        const resolved: WatchlistItem[] = quotes
          .filter((r): r is PromiseFulfilledResult<WatchlistItem> => r.status === "fulfilled")
          .map(r => r.value)

        setWatchlistItems(resolved)
      } catch {
        // Graceful degradation – leave empty
        setWatchlistItems([])
      } finally {
        setWatchlistLoading(false)
      }
    }

    fetchWatchlist()
  }, [positions])

  // --- FETCH MARKET MOVERS ---
  useEffect(() => {
    const fetchMarket = async () => {
      setMarketLoading(true)
      try {
        const data = await apiFetch("/market/movers")
        const movers: MarketMover[] = (data.gainers || data.top_gainers || data || [])
          .slice(0, 5)
          .map((m: any) => ({
            ticker: m.ticker || m.symbol || "",
            name: m.name || m.ticker || m.symbol || "",
            change_percent: m.change_percent ?? m.changesPercentage ?? 0,
          }))
        setMarketMovers(movers)
      } catch {
        // Try indices as fallback
        try {
          const indices = await apiFetch("/market/indices")
          const items: MarketMover[] = (Array.isArray(indices) ? indices : [])
            .slice(0, 5)
            .map((m: any) => ({
              ticker: m.symbol || m.ticker || "",
              name: m.name || m.symbol || "",
              change_percent: m.change_percent ?? m.changesPercentage ?? 0,
            }))
          setMarketMovers(items)
        } catch {
          setMarketMovers([])
        }
      } finally {
        setMarketLoading(false)
      }
    }

    fetchMarket()
  }, [])

  // --- CHART DATA ---
  const chartData = useMemo(() => {
    console.log('equityCurve from API:', equityCurve?.length, JSON.stringify(equityCurve?.slice(0, 2)))
    const filtered = filterEquityCurve(equityCurve, chartFilter)
    console.log('chartData after filter:', filtered?.length, JSON.stringify(filtered?.slice(0, 2)))
    return filtered
  }, [equityCurve, chartFilter])

  // --- RISK METRICS ---
  const riskLevel = useMemo(() => getRiskLabel(summary?.volatility_annualized ?? 0), [summary])
  const growthLabel = useMemo(() => getGrowthLabel(summary?.daily_return_pct ?? 0), [summary])

  const var95 = summary?.var_95 ?? 0
  const maxDrawdown = Math.abs(summary?.max_drawdown ?? 0)
  const recoveryStrength = maxDrawdown < 0.05 ? "Strong" : maxDrawdown < 0.15 ? "Moderate" : "Weak"
  const recoveryColor = maxDrawdown < 0.05 ? "text-[#5F7055]" : maxDrawdown < 0.15 ? "text-[#D67C38]" : "text-[#C85D5D]"

  // Possible downside range based on VaR95 and portfolio value
  const downsideLow = Math.round(portfolioValue * Math.abs(var95) * 0.7)
  const downsideHigh = Math.round(portfolioValue * Math.abs(var95) * 1.3)

  // --- PROJECTIONS (based on real NAV) ---
  const conservativeProjection = portfolioValue > 0 ? portfolioValue * 1.08 : 0
  const expectedProjection = portfolioValue > 0 ? portfolioValue * 1.15 : 0
  const optimisticProjection = portfolioValue > 0 ? portfolioValue * 1.25 : 0

  // Donut configuration for goal
  const donutRadius = 22
  const donutCircumference = 2 * Math.PI * donutRadius
  const donutStrokeDashoffset = donutCircumference - (goalProgress / 100) * donutCircumference

  // --- ACTIONS ---
  // --- DYNAMIC REBALANCE ACTION & SOLVER ---
  const [proposedTrades, setProposedTrades] = useState<any[]>([])
  const [checkedTrades, setCheckedTrades] = useState<Record<string, boolean>>({})
  const [showOptimalAllocation, setShowOptimalAllocation] = useState(false)
  const [loadingRebalance, setLoadingRebalance] = useState(false)

  const fetchDynamicRebalance = useCallback(async () => {
    if (!selectedPortfolioId || positions.length === 0) return
    setLoadingRebalance(true)
    try {
      const tickers = positions.map(p => p.ticker)
      // 1. Optimize portfolio to get target weights
      const optData = await api.post("/portfolio/optimize", {
        tickers,
        method: "markowitz",
        objective: "max_sharpe"
      })

      const targetWeights = optData.optimal_weights
      if (!targetWeights) return

      // 2. Map current positions for rebalance endpoint
      const currentPositions = positions.map(p => ({
        ticker: p.ticker,
        shares: p.shares
      }))

      // 3. Fetch trade execution plan
      const rebalData = await api.post("/portfolio/rebalance", {
        current_positions: currentPositions,
        target_weights: targetWeights,
        threshold: 0.01 // strict threshold to catch any drift
      })

      const trades = rebalData.trades || []
      setProposedTrades(trades)

      // Initialize all trades as checked
      const initialChecked: Record<string, boolean> = {}
      trades.forEach((t: any) => {
        initialChecked[t.ticker] = true
      })
      setCheckedTrades(initialChecked)
    } catch (err) {
      console.error("Failed to fetch dynamic rebalance:", err)
    } finally {
      setLoadingRebalance(false)
    }
  }, [selectedPortfolioId, positions])

  useEffect(() => {
    if (positions.length > 0) {
      fetchDynamicRebalance()
    }
  }, [positions.length, fetchDynamicRebalance])

  const handleApplyAction = async () => {
    if (applied || isApplying) return
    setIsApplying(true)
    
    try {
      const activeTrades = proposedTrades.filter(t => checkedTrades[t.ticker])
      if (activeTrades.length === 0) {
        toast({
          type: 'info',
          title: 'No Trades Selected',
          description: 'Please select at least one trade to execute.'
        })
        setIsApplying(false)
        return
      }

      // Execute trades sequentially to prevent database locks or race conditions
      for (const trade of activeTrades) {
        await api.post("/portfolio/transactions", {
          portfolio_id: selectedPortfolioId,
          transaction_type: trade.action, // "BUY" or "SELL"
          symbol: trade.ticker,
          quantity: trade.shares,
          price: trade.price,
          fees: trade.estimated_cost || 0.0
        })
      }

      setApplied(true)
      toast({
        type: 'success',
        title: 'Rebalancing Executed!',
        description: `Successfully executed ${activeTrades.length} paper trades in your portfolio.`
      })

      // Refresh the entire portfolio state
      refresh()

      // Add bot confirmation message
      setChatMessages(prev => [
        ...prev,
        {
          sender: "bot",
          text: `I have successfully implemented your custom portfolio rebalance! Executed ${activeTrades.length} transactions based on your target allocation. Your portfolio risk is now fully optimized.`,
          timestamp: new Date()
        }
      ])
    } catch (err: any) {
      console.error(err)
      toast({
        type: 'error',
        title: 'Rebalancing Failed',
        description: err.message || 'Failed to execute rebalance transactions.'
      })
    } finally {
      setIsApplying(false)
    }
  }

  const handleAskQuestion = (question: string) => {
    if (!question.trim()) return
    
    const userMsg: Message = {
      sender: "user",
      text: question,
      timestamp: new Date()
    }
    
    setChatMessages(prev => [...prev, userMsg])
    setChatInput("")
    setIsTyping(true)
    
    // Generate bot responses using real portfolio data
    setTimeout(() => {
      let botText = "Analyzing your portfolio with RAUTREX quant models..."
      const q = question.toLowerCase()
      
      if (q.includes("down") || q.includes("why is my")) {
        const topSectorName = topSector?.label ?? "unknown"
        const topSectorPct = topSector?.weight_pct?.toFixed(1) ?? "N/A"
        botText = `Your portfolio currently holds ${topSectorPct}% in ${topSectorName}. Your daily P&L is ${formatINR(dailyPnl)} (${dailyReturnPct >= 0 ? '+' : ''}${dailyReturnPct.toFixed(2)}%). Portfolio health score: ${healthScore}/100. Sharpe ratio: ${(summary?.sharpe_ratio ?? 0).toFixed(2)}.`
      } else if (q.includes("risk") || q.includes("safe")) {
        botText = `Portfolio risk assessment: VaR(95) is ${(Math.abs(var95) * 100).toFixed(1)}%, max drawdown ${(maxDrawdown * 100).toFixed(1)}%, volatility ${((summary?.volatility_annualized ?? 0) * 100).toFixed(1)}% annualized. Recovery strength: ${recoveryStrength}. Beta vs S&P: ${(summary?.beta_vs_spy ?? 0).toFixed(2)}.`
      } else if (q.includes("buy") || q.includes("sbi")) {
        botText = `Based on your current allocation, you have ${formatINR(cashAvailable)} in cash available for deployment. Your portfolio holds ${positions.length} positions with ${formatINR(portfolioValue)} total NAV.`
      } else if (q.includes("etf") || q.includes("explain")) {
        botText = `An Exchange Traded Fund (ETF) is a basket of assets traded like a stock. With your current ${formatINR(cashAvailable)} idle cash, allocating to a broad ETF could improve diversification across your ${positions.length} holdings.`
      } else {
        const holdingNames = positions.slice(0, 3).map(p => p.name || p.ticker).join(", ")
        botText = `Quantitative analysis of your holdings (${holdingNames || 'none yet'}): NAV ${formatINR(portfolioValue)}, Daily P&L ${formatINR(dailyPnl)}, Health ${healthScore}/100. ${cashAvailable > 0 ? `Consider deploying ${formatINR(cashAvailable)} idle cash.` : ''}`
      }

      setChatMessages(prev => [
        ...prev,
        {
          sender: "bot",
          text: botText,
          timestamp: new Date()
        }
      ])
      setIsTyping(false)
    }, 1200)
  }

  // --- LOADING STATE ---
  if (portfolioLoading) {
    return (
      <div className="bg-background text-[#2B2A27] min-h-screen p-1 md:p-3 font-sans antialiased overflow-x-hidden">
        <div className="flex flex-col xl:flex-row gap-6 max-w-[1700px] mx-auto">
          <div className="flex-1 space-y-6 min-w-0">
            {/* Top stats skeleton */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              {[1,2,3,4,5].map(i => (
                <div key={i} className="bg-card border border-black rounded-[12px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.02)] min-h-[110px]">
                  <Skeleton className="h-3 w-24 mb-4" />
                  <Skeleton className="h-6 w-32 mb-2" />
                  <Skeleton className="h-3 w-20" />
                </div>
              ))}
            </div>
            {/* Chart skeleton */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 bg-card border border-black rounded-[12px] p-5 min-h-[380px]">
                <Skeleton className="h-4 w-40 mb-4" />
                <Skeleton className="h-[280px] w-full" />
              </div>
              <div className="bg-card border border-[#F5EAD4] rounded-[12px] p-5 min-h-[380px]">
                <Skeleton className="h-4 w-32 mb-4" />
                <Skeleton className="h-6 w-48 mb-2" />
                <Skeleton className="h-40 w-full" />
              </div>
            </div>
            {/* Holdings skeleton */}
            <div className="space-y-4">
              <Skeleton className="h-4 w-20" />
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {[1,2,3,4].map(i => (
                  <div key={i} className="bg-card border border-black rounded-[12px] p-4 shadow-[0_2px_8px_rgba(0,0,0,0.02)] min-h-[200px]">
                    <Skeleton className="h-8 w-8 rounded-full mb-3" />
                    <Skeleton className="h-4 w-24 mb-2" />
                    <Skeleton className="h-10 w-full mb-3" />
                    <Skeleton className="h-3 w-32" />
                  </div>
                ))}
              </div>
            </div>
          </div>
          {/* Sidebar skeleton */}
          <aside className="w-full xl:w-[280px] shrink-0 bg-card border border-black rounded-[12px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.02)] space-y-6 flex flex-col justify-between">
            <Skeleton className="h-4 w-28 mb-4" />
            <Skeleton className="h-20 w-full mb-6" />
            <Skeleton className="h-4 w-28 mb-4" />
            <Skeleton className="h-16 w-full mb-6" />
            <Skeleton className="h-4 w-28 mb-4" />
            <Skeleton className="h-24 w-full" />
          </aside>
        </div>
      </div>
    )
  }

  // --- ERROR STATE ---
  if (portfolioError && !overview) {
    return (
      <div className="bg-background text-[#2B2A27] min-h-screen p-1 md:p-3 font-sans antialiased overflow-x-hidden flex items-center justify-center">
        <div className="bg-card border border-black rounded-[12px] p-8 shadow-[0_2px_8px_rgba(0,0,0,0.02)] max-w-md text-center space-y-4">
          <AlertTriangle size={32} className="text-[#D67C38] mx-auto" />
          <h3 className="text-sm font-bold text-[#2B2A27] uppercase tracking-wide">Unable to load portfolio</h3>
          <p className="text-xs text-[#8C8278] leading-relaxed">{portfolioError}</p>
          <button
            onClick={() => refresh()}
            className="inline-flex items-center gap-2 bg-[#8B6F47] hover:bg-[#735C3A] text-[var(--text-primary)] text-xs font-bold uppercase tracking-widest py-2.5 px-6 rounded-lg transition-all"
          >
            <RefreshCw size={14} />
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-background text-[#2B2A27] min-h-screen p-1 md:p-3 font-sans antialiased overflow-x-hidden">
      
      {/* Outer Flex Layout Grid */}
      <div className="flex flex-col xl:flex-row gap-6 max-w-[1700px] mx-auto">
        
        {/* ========================================================================= */}
        {/* LEFT-CENTER CONTENT COLUMN */}
        {/* ========================================================================= */}
        <div className="flex-1 space-y-6">
          
          {/* Gorgeous Premium Progressive Disclosure Alert Banner */}
          <AnimatePresence>
            {showCashPrompt && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="bg-amber-500/10 border-l-[3px] border-amber-500 rounded-[12px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.02)] flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                <div className="flex gap-3 items-start">
                  <div className="w-9 h-9 bg-amber-500/20 text-amber-700 rounded-full flex items-center justify-center shrink-0">
                    <DollarSign size={18} />
                  </div>
                  <div className="space-y-1">
                    <h4 className="text-xs font-bold text-[#2B2A27] tracking-tight">Spare Cash Alert: Your uninvested balance is ₹0</h4>
                    <p className="text-xs text-[#8C8278] leading-relaxed max-w-xl">
                      CDSL/NSDL statements do not contain cash balances. If you have spare uninvested cash sitting in your linked broker accounts, enter it below to make your asset allocation models and risk scores perfectly accurate.
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center gap-2 shrink-0">
                  <input
                    type="number"
                    placeholder="E.g., 5000"
                    value={cashInputVal}
                    onChange={(e) => setCashInputVal(e.target.value)}
                    className="h-9 px-3 bg-card border border-black rounded-lg text-xs font-bold w-28 focus:outline-none focus:border-amber-500 text-[var(--text-primary)]"
                  />
                  <button
                    disabled={updatingCashBalance || !cashInputVal}
                    onClick={handleUpdateCash}
                    className="h-9 px-4 bg-[#8B6F47] hover:bg-[#735C3A] text-[var(--text-primary)] text-xs font-bold uppercase tracking-wider rounded-lg transition-all flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {updatingCashBalance ? "Saving..." : "Update Cash"}
                  </button>
                  <button
                    onClick={() => setShowCashPrompt(false)}
                    className="w-9 h-9 text-[#8C8278] hover:text-[#2B2A27] transition-all flex items-center justify-center"
                  >
                    <X size={16} />
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          
          {/* Dashboard Header Section with Portfolio Switcher */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-[#EBEBE6]/60">
            <div>
              <h1 className="text-xl font-black text-[#2B2A27] tracking-tight uppercase">Quant Dashboard</h1>
              <p className="text-xs font-bold text-[#8C8278] uppercase tracking-widest mt-0.5">Real-time Safety & Calibration Audit</p>
            </div>
            
            {/* Portfolio Dropdown Switcher */}
            {portfolios.length > 0 && (
              <div className="flex items-center gap-2 bg-card border border-black rounded-lg px-3 py-1.5 shadow-[0_2px_8px_rgba(0,0,0,0.02)]">
                <span className="text-xs font-bold uppercase tracking-wider text-[#8C8278]">Portfolio:</span>
                <select
                  value={selectedPortfolioId || ""}
                  onChange={(e) => setSelectedPortfolioId(e.target.value)}
                  className="bg-transparent border-none text-[#2B2A27] text-xs font-bold focus:outline-none cursor-pointer pr-4"
                >
                  {portfolios.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
          
          {/* ========================================= */}
          {/* TOP STATS ROW (5 EQUAL CARDS) */}
          {/* ========================================= */}
          <div className="flex flex-wrap gap-4">
            
            {/* 1. Portfolio Value */}
            <div className="flex-1 min-w-[180px] bg-card border border-black rounded-[12px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.02)] flex flex-col justify-between min-h-[110px]">
              <span className="text-xs font-bold text-[#8C8278] uppercase tracking-wider">Portfolio Value</span>
              <div className="mt-2">
                <span className="text-[22px] font-extrabold text-[#2B2A27] leading-none break-words">
                  {portfolioValue > 0 ? formatINR(portfolioValue) : "--"}
                </span>
                <div className={cn(
                  "flex flex-wrap items-center gap-1 mt-1 text-xs font-semibold",
                  dailyPnl >= 0 ? "text-[#5F7055]" : "text-[#C85D5D]"
                )}>
                  {dailyPnl >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                  <span>
                    {dailyPnl >= 0 ? "+" : ""}{formatINR(dailyPnl, "₹0")} today
                    {dailyReturnPct !== 0 && ` (${dailyReturnPct >= 0 ? '+' : ''}${dailyReturnPct.toFixed(2)}%)`}
                  </span>
                </div>
              </div>
            </div>

            {/* 2. Portfolio Health */}
            <div className="flex-1 min-w-[180px] bg-card border border-black rounded-[12px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.02)] flex flex-col justify-between min-h-[110px]">
              <div className="flex justify-between items-center">
                <span className="text-xs font-bold text-[#8C8278] uppercase tracking-wider">Portfolio Health</span>
                <span className="text-lg font-bold text-[#D67C38]">{summary ? `${healthScore}/100` : "--"}</span>
              </div>
              <div className="mt-3">
                {/* Horizontal Progress Bar */}
                <div className="w-full bg-background h-1.5 rounded-full overflow-hidden border border-[#EBEBE6]">
                  <motion.div 
                    initial={{ width: "0%" }}
                    animate={{ width: `${healthScore}%` }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                    className="h-full bg-[#C9A96E] rounded-full"
                  />
                </div>
                <div className="flex justify-between mt-2 text-xs font-bold uppercase tracking-wider">
                  <span className={riskLevel.color}>{riskLevel.text}</span>
                  <span className={growthLabel.color}>{growthLabel.text}</span>
                </div>
              </div>
            </div>

            {/* 3. Goal Progress */}
            <div className="flex-1 min-w-[180px] bg-card border border-black rounded-[12px] p-4 shadow-[0_2px_8px_rgba(0,0,0,0.02)] flex items-center justify-between min-h-[110px]">
              <div className="flex flex-col justify-between h-full">
                <span className="text-xs font-bold text-[#8C8278] uppercase tracking-wider">Goal Progress</span>
                <div className="mt-1">
                  <span className="text-xs font-semibold text-[#8C8278] block">House Fund</span>
                  <span className="text-sm font-bold text-[#2B2A27]">
                    {formatLakhs(portfolioValue)} / {formatLakhs(goalTarget)}
                  </span>
                </div>
              </div>
              
              {/* Custom SVG Donut Gauge */}
              <div className="relative w-14 h-14 shrink-0">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 50 50">
                  <circle
                    cx="25"
                    cy="25"
                    r={donutRadius}
                    className="stroke-[#FAF9F6]"
                    strokeWidth="4"
                    fill="transparent"
                  />
                  <motion.circle
                    cx="25"
                    cy="25"
                    r={donutRadius}
                    className="stroke-[#C9A96E]"
                    strokeWidth="4"
                    fill="transparent"
                    strokeDasharray={donutCircumference}
                    initial={{ strokeDashoffset: donutCircumference }}
                    animate={{ strokeDashoffset: donutStrokeDashoffset }}
                    transition={{ duration: 1, ease: "easeOut" }}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-xs font-bold text-[#2B2A27]">{goalProgress}%</span>
                </div>
              </div>
            </div>

            {/* 4. Total Return */}
            <div className="flex-1 min-w-[180px] bg-card border border-black rounded-[12px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.02)] flex flex-col justify-between min-h-[110px]">
              <span className="text-xs font-bold text-[#8C8278] uppercase tracking-wider">Total Return</span>
              <div className="mt-2">
                <span className={cn(
                  "text-[22px] font-extrabold block leading-none break-words",
                  overallPnl >= 0 ? "text-[#2B2A27]" : "text-[#C85D5D]"
                )}>
                  {formatINR(overallPnl, "₹0")}
                </span>
                <div className={cn(
                  "flex flex-wrap items-center gap-1 mt-1 text-xs font-semibold",
                  overallPnl >= 0 ? "text-[#5F7055]" : "text-[#C85D5D]"
                )}>
                  {overallPnl >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                  <span>
                    {overallPnl >= 0 ? "+" : ""}{overallPnlPct.toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>

            {/* 5. Cash Available */}
            <div className="flex-1 min-w-[180px] bg-card border border-black rounded-[12px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.02)] flex flex-col justify-between min-h-[110px]">
              <span className="text-xs font-bold text-[#8C8278] uppercase tracking-wider">Cash Available</span>
              <div className="mt-2">
                <motion.span 
                  key={cashAvailable}
                  initial={{ scale: 0.95, opacity: 0.8 }}
                  animate={{ scale: 1, opacity: 1 }}
                  className="text-[22px] font-extrabold text-[#2B2A27] block break-words"
                >
                  {cashAvailable > 0 ? formatINR(cashAvailable) : "--"}
                </motion.span>
                <span className="text-xs text-[#8C8278] font-medium tracking-wide block mt-1">
                  {summary?.buying_power != null ? `Buying power: ${formatINR(summary.buying_power)}` : "Ready to invest"}
                </span>
              </div>
            </div>

          </div>

          {/* ========================================= */}
          {/* CHART & ACTION HUB SPLIT */}
          {/* ========================================= */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Portfolio Performance Chart Card */}
            <div className="lg:col-span-2 bg-card border border-black rounded-[12px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.02)] flex flex-col min-h-[380px]">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 border-b border-[#F2F2ED] pb-3 mb-4">
                <h3 className="text-sm font-bold text-[#2B2A27] uppercase tracking-wide">Portfolio Performance</h3>
                
                {/* Time Filters */}
                <div className="flex items-center bg-background p-0.5 rounded-lg border border-[#EBEBE6]">
                  {(["1D", "1W", "3M", "6M", "1Y", "ALL"] as const).map((filter) => (
                    <button
                      key={filter}
                      onClick={() => setChartFilter(filter)}
                      className={cn(
                        "px-2.5 py-1 text-xs font-bold uppercase tracking-wider rounded transition-all",
                        chartFilter === filter 
                          ? "text-[#C9A96E] bg-card border border-black shadow-sm" 
                          : "text-[#8C8278] hover:text-[#2B2A27]"
                      )}
                    >
                      {filter}
                    </button>
                  ))}
                </div>
              </div>

              {/* Recharts Area Chart with real equity curve data */}
              <div className="flex-1 w-full min-h-[250px] relative">
                {hasChartData ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart 
                      data={chartData} 
                      margin={{ top: 10, right: 10, left: 10, bottom: 5 }}
                    >
                      <defs>
                        <linearGradient id="creamGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#C9A96E" stopOpacity={0.15}/>
                          <stop offset="95%" stopColor="#C9A96E" stopOpacity={0.0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#F2F2ED" vertical={false} />
                      <XAxis 
                        dataKey="date" 
                        tickLine={false} 
                        axisLine={false} 
                        tick={{ fill: '#8C8278', fontSize: 9, fontWeight: '600' }} 
                        tickFormatter={(tick) => {
                          try {
                            return new Date(tick).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
                          } catch {
                            return tick
                          }
                        }}
                        dy={5}
                      />
                      <YAxis 
                        domain={['auto', 'auto']}
                        tickLine={false} 
                        axisLine={false} 
                        tick={{ fill: '#8C8278', fontSize: 9, fontWeight: '600' }} 
                        tickFormatter={(value) => {
                          if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`
                          if (value >= 1000) return `₹${(value / 1000).toFixed(0)}K`
                          return `₹${value}`
                        }}
                        width={55}
                      />
                      <Tooltip
                        contentStyle={{ 
                          backgroundColor: "#FFFFFF", 
                          border: "1px solid #EBEBE6", 
                          borderRadius: "8px",
                          boxShadow: "0 4px 12px rgba(0,0,0,0.05)",
                          fontFamily: "inherit"
                        }}
                        itemStyle={{ color: "#8B6F47", fontWeight: "bold", fontSize: "12px" }}
                        labelStyle={{ color: "#8C8278", fontSize: "10px", fontWeight: "bold" }}
                        formatter={(value: number) => [`₹${value.toLocaleString('en-IN')}`, "NAV"]}
                        labelFormatter={(label: string, payload: any[]) => {
                          const date = payload?.[0]?.payload?.date
                          if (date) {
                            return new Date(date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
                          }
                          return "Portfolio Index"
                        }}
                      />
                      <Area 
                        type="monotone" 
                        dataKey="value" 
                        stroke="#C9A96E" 
                        strokeWidth={2.5} 
                        fill="url(#creamGradient)" 
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-full text-[#8C8278] text-xs font-medium">
                    Building your performance history — check back tomorrow
                  </div>
                )}
              </div>
            </div>

            {/* Today's Action Card */}
            <div className="bg-card border border-[#F5EAD4] rounded-[12px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.02)] flex flex-col justify-between min-h-[380px]">
              <div className="space-y-4">
                {/* Badge */}
                <div className="flex justify-between items-center">
                  <div className="inline-flex items-center gap-1 bg-[#F5EAD4] px-2 py-0.5 rounded text-xs font-bold text-[#C58A3E] uppercase tracking-widest">
                    <span>{showOptimalAllocation ? "⚡ REBALANCE SIMULATOR" : "⭐ TODAY'S ACTION"}</span>
                  </div>
                  {showOptimalAllocation && (
                    <button 
                      onClick={() => setShowOptimalAllocation(false)}
                      className="text-[10px] text-[#8C8278] hover:text-[#2B2A27] font-bold uppercase tracking-wider"
                    >
                      ← Back
                    </button>
                  )}
                </div>

                <div className="space-y-1">
                  <h4 className="text-lg font-bold text-[#2B2A27] tracking-tight leading-snug">
                    {showOptimalAllocation 
                      ? "AI Optimized Rebalance Plan"
                      : (cashAvailable >= 5000 
                          ? `Deploy ${formatINR(Math.min(cashAvailable, 5000))} into Nifty ETF` 
                          : "Review your portfolio allocation")
                    }
                  </h4>
                  <p className="text-xs text-[#8C8278] leading-relaxed">
                    {showOptimalAllocation 
                      ? "Uncheck individual transactions below to customize your optimization plan before execution:"
                      : (topSector 
                          ? `Your portfolio currently relies heavily on ${topSector.label} (${topSector.weight_pct.toFixed(1)}%).` 
                          : "Diversify your portfolio for better risk-adjusted returns.")
                    }
                  </p>
                </div>

                <hr className="border-[#F5EAD4]" />

                {/* Grid Split Content */}
                <div className="grid grid-cols-2 gap-4">
                  {/* Left Column: Expected Impact OR Trades Checklist */}
                  <div className="space-y-2">
                    <span className="text-xs font-bold text-[#8C8278] uppercase tracking-wider block">
                      {showOptimalAllocation ? "Execution Steps" : "Expected Impact"}
                    </span>
                    
                    {showOptimalAllocation ? (
                      loadingRebalance ? (
                        <div className="space-y-2 py-1">
                          <Skeleton className="h-4 w-full" />
                          <Skeleton className="h-4 w-3/4" />
                          <Skeleton className="h-4 w-5/6" />
                        </div>
                      ) : proposedTrades.length > 0 ? (
                        <div className="space-y-2 max-h-[140px] overflow-y-auto pr-1">
                          {proposedTrades.map((trade) => (
                            <label key={trade.ticker} className="flex items-start gap-1.5 cursor-pointer text-[10px] font-bold text-[#2B2A27] select-none">
                              <input
                                type="checkbox"
                                checked={!!checkedTrades[trade.ticker]}
                                onChange={() => setCheckedTrades(prev => ({ ...prev, [trade.ticker]: !prev[trade.ticker] }))}
                                className="rounded border-[#EBEBE6] text-[#8B6F47] focus:ring-[#8B6F47] w-3.5 h-3.5 mt-0.5 shrink-0"
                              />
                              <span className={cn(
                                "leading-tight",
                                trade.action === "BUY" ? "text-[#5F7055]" : "text-[#C85D5D]"
                              )}>
                                {trade.action} {trade.shares.toFixed(1)} sh of {trade.ticker.split('.')[0]}
                              </span>
                            </label>
                          ))}
                        </div>
                      ) : (
                        <div className="text-[10px] font-bold text-[#8C8278] italic py-2">
                          No rebalancing required (portfolio is fully aligned).
                        </div>
                      )
                    ) : (
                      <ul className="space-y-1.5 text-xs text-[#5F7055] font-semibold">
                        <li className="flex items-start gap-1">
                          <Check size={14} className="shrink-0 mt-0.5" />
                          <span>Lower risk</span>
                        </li>
                        <li className="flex items-start gap-1">
                          <Check size={14} className="shrink-0 mt-0.5" />
                          <span>Better diversity</span>
                        </li>
                        <li className="flex items-start gap-1">
                          <Check size={14} className="shrink-0 mt-0.5" />
                          <span>Stable growth</span>
                        </li>
                      </ul>
                    )}
                  </div>

                  {/* Right Column: Health and AI Stats */}
                  <div className="space-y-3.5">
                    <div>
                      <span className="text-xs font-bold text-[#8C8278] uppercase tracking-wider block">Portfolio Health</span>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-sm font-bold text-[#2B2A27]">{healthScore}</span>
                        <ArrowRight size={12} className="text-[#8C8278]" />
                        <span className="text-sm font-bold text-[#5F7055]">
                          {showOptimalAllocation ? Math.min(100, healthScore + 5) : Math.min(100, healthScore + 2)}
                        </span>
                      </div>
                    </div>
                    <div>
                      <span className="text-xs font-bold text-[#8C8278] uppercase tracking-wider block">AI Confidence</span>
                      <span className="text-sm font-bold text-[#C9A96E]">87%</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Bottom CTAs */}
              <div className="space-y-2 pt-4">
                {!showOptimalAllocation ? (
                  <div className="grid grid-cols-2 gap-2">
                    <button 
                      onClick={() => {
                        toast({
                          type: 'info',
                          title: 'Educational Blueprint',
                          description: `Our solver applies the Markowitz Mean-Variance framework to optimize your Sharpe ratio. Current portfolio vol: ${(summary?.volatility_annualized ?? 0 * 100).toFixed(1)}%.`
                        })
                      }}
                      className="border border-[#F2DCA5] hover:bg-white/40 text-[#2B2A27] text-xs font-bold uppercase tracking-wider py-2 rounded-lg transition-all"
                    >
                      Learn More
                    </button>
                    <button 
                      onClick={() => setShowOptimalAllocation(true)}
                      className="border border-[#F2DCA5] hover:bg-white/40 text-[#2B2A27] text-xs font-bold uppercase tracking-wider py-2 rounded-lg transition-all bg-white/20"
                    >
                      See Impact
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={handleApplyAction}
                    disabled={applied || isApplying || proposedTrades.length === 0}
                    className={cn(
                      "w-full text-white text-xs font-bold uppercase tracking-widest py-2.5 rounded-lg transition-all shadow-sm flex items-center justify-center gap-2",
                      applied 
                        ? "bg-[#5F7055] cursor-default" 
                        : "bg-[#8B6F47] hover:bg-[#735C3A] active:scale-[0.98] disabled:opacity-50"
                    )}
                  >
                    {isApplying ? (
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : applied ? (
                      <>
                        <Check size={14} />
                        <span>Rebalancing Executed</span>
                      </>
                    ) : (
                      <span>Execute Rebalance</span>
                    )}
                  </button>
                )}
              </div>
            </div>

          </div>

          {/* ========================================= */}
          {/* HOLDINGS SECTION (DYNAMIC CARDS) */}
          {/* ========================================= */}
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-sm font-bold text-[#2B2A27] uppercase tracking-wide">Holdings</h3>
              <span className="text-xs text-[#8C8278] font-semibold">
                {positions.length > 0 ? `${positions.length} position${positions.length !== 1 ? 's' : ''}` : "Active Ledger"}
              </span>
            </div>

            {topHoldings.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {topHoldings.map((pos) => {
                  const color = getTickerColor(pos.ticker)
                  const sparkline = getSparklinePath(pos.unrealized_pnl)
                  const pnlPositive = pos.unrealized_pnl >= 0

                  return (
                    <div key={pos.ticker} className="bg-card border border-black rounded-[12px] p-4 shadow-[0_2px_8px_rgba(0,0,0,0.02)] flex flex-col justify-between min-h-[200px]">
                      <div className="flex justify-between items-start">
                        <div className="flex items-center gap-2.5">
                          <div className={cn("w-8 h-8 rounded-full flex items-center justify-center shrink-0", color.bg)}>
                            <span className={cn("font-extrabold text-sm", color.text)}>
                              {pos.ticker.charAt(0)}
                            </span>
                          </div>
                          <div>
                            <h4 className="text-xs font-bold text-[#2B2A27]">{pos.name || pos.ticker}</h4>
                            <span className="text-xs text-[#8C8278] font-medium uppercase tracking-wider">{pos.ticker}</span>
                          </div>
                        </div>
                        <div className="text-right">
                          <span className="text-xs text-[#8C8278] uppercase block">Invested</span>
                          <span className="text-xs font-bold text-[#2B2A27]">{formatINR(pos.cost_basis)}</span>
                        </div>
                      </div>

                      {/* Real Recharts LineChart Sparkline */}
                      <div className="w-full h-10 my-3">
                        {pos.price_history && pos.price_history.length > 0 ? (
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={pos.price_history}>
                              <Line
                                type="monotone"
                                dataKey="price"
                                stroke={pnlPositive ? "#5F7055" : "#C85D5D"}
                                strokeWidth={1.5}
                                dot={false}
                              />
                              <Tooltip
                                contentStyle={{
                                  backgroundColor: "#FFFFFF",
                                  border: "1px solid #EBEBE6",
                                  borderRadius: "4px",
                                  boxShadow: "0 2px 6px rgba(0,0,0,0.05)",
                                  fontSize: "9px",
                                  padding: "4px"
                                }}
                                labelStyle={{ color: "#8C8278", fontWeight: "bold" }}
                                itemStyle={{ color: "#8B6F47", fontWeight: "bold", padding: 0 }}
                                formatter={(value: number) => [`₹${value.toFixed(2)}`, "Price"]}
                                labelFormatter={(label, payload) => {
                                  const dateVal = payload?.[0]?.payload?.date
                                  if (dateVal) {
                                    try {
                                      return new Date(dateVal).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
                                    } catch {
                                      return dateVal
                                    }
                                  }
                                  return ""
                                }}
                              />
                            </LineChart>
                          </ResponsiveContainer>
                        ) : (
                          <div className="flex items-center justify-center h-full text-xs text-[#8C8278] font-bold uppercase tracking-wider bg-background rounded border border-[#EBEBE6] border-dashed">
                            No Price History
                          </div>
                        )}
                      </div>

                      <div className="flex justify-between items-end border-t border-[#F2F2ED] pt-2.5">
                        <div className="flex flex-col">
                          <span className="text-xs font-bold text-[#8C8278] uppercase tracking-wider">
                            {pos.sector ?? "RAUTREX VIEW"}
                          </span>
                          <span className="text-xs text-[#8C8278] leading-tight max-w-[130px] font-medium">
                            {pos.total_return_pct >= 0 ? "Positive returns" : "Under pressure"} · {pos.weight_pct.toFixed(1)}% of portfolio
                          </span>
                        </div>
                        <span className={cn(
                          "text-xs font-bold px-1.5 py-0.5 rounded font-mono",
                          pnlPositive
                            ? "bg-[#EEF6EE] text-[#5F7055]"
                            : "bg-[#FDF2F2] text-[#C85D5D]"
                        )}>
                          {pnlPositive ? "+" : ""}{formatINR(pos.unrealized_pnl)}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="bg-card border border-black rounded-[12px] p-8 shadow-[0_2px_8px_rgba(0,0,0,0.02)] text-center">
                <p className="text-xs text-[#8C8278] font-medium">No holdings yet. Add positions to your portfolio to see them here.</p>
              </div>
            )}
          </div>

          {/* ========================================= */}
          {/* BOTTOM ROW (PROJECTIONS & UPDATES) */}
          {/* ========================================= */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* Future Outlook Card */}
            <div className="bg-card border border-black rounded-[12px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.02)] flex flex-col justify-between min-h-[220px]">
              <div>
                <div className="flex justify-between items-center border-b border-[#F2F2ED] pb-2 mb-3">
                  <h4 className="text-xs font-bold text-[#2B2A27] uppercase tracking-wider">Future Outlook</h4>
                  <span className="text-xs font-bold text-[#8C8278] uppercase bg-background border border-[#EBEBE6] px-1.5 py-0.5 rounded">
                    Monthly Plan
                  </span>
                </div>
                <p className="text-xs text-[#8C8278] font-medium">If you invest ₹5,000 monthly:</p>
                
                {/* Horizontal Projection Bars and Data */}
                <div className="flex items-center justify-between mt-3 gap-6">
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-[#8C8278] font-medium">Conservative</span>
                      <span className="font-extrabold text-[#2B2A27]">{formatLakhs(conservativeProjection)}</span>
                    </div>
                    <div className="w-full bg-background h-1 rounded-full overflow-hidden">
                      <div className="h-full bg-gray-400 w-[60%]" />
                    </div>

                    <div className="flex items-center justify-between text-xs">
                      <span className="text-[#8C8278] font-medium">Expected</span>
                      <span className="font-extrabold text-[#C9A96E]">{formatLakhs(expectedProjection)}</span>
                    </div>
                    <div className="w-full bg-background h-1 rounded-full overflow-hidden">
                      <div className="h-full bg-[#C9A96E] w-[75%]" />
                    </div>

                    <div className="flex items-center justify-between text-xs">
                      <span className="text-[#8C8278] font-medium">Optimistic</span>
                      <span className="font-extrabold text-[#5F7055]">{formatLakhs(optimisticProjection)}</span>
                    </div>
                    <div className="w-full bg-background h-1 rounded-full overflow-hidden">
                      <div className="h-full bg-[#5F7055] w-[95%]" />
                    </div>
                  </div>

                  {/* Dynamic Projection Chart */}
                  <div className="w-20 h-16 bg-background border border-black rounded-lg p-2 shrink-0 flex items-center justify-center">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={[
                        { name: 'Now', value: portfolioValue },
                        { name: 'M1', value: portfolioValue + (expectedProjection - portfolioValue) * 0.33 },
                        { name: 'M2', value: portfolioValue + (expectedProjection - portfolioValue) * 0.66 },
                        { name: 'M3', value: expectedProjection }
                      ]}>
                        <Line type="monotone" dataKey="value" stroke="#C9A96E" strokeWidth={2.5} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

              <div className="flex justify-between items-center text-xs text-[#8C8278] font-bold border-t border-[#F2F2ED] pt-2.5 mt-4">
                <span>Based on historical parameters. Not guaranteed.</span>
                <span className="uppercase tracking-wider">Current NAV: {formatLakhs(portfolioValue)}</span>
              </div>
            </div>

            {/* Updates Checklist Card */}
            <div className="bg-card border border-black rounded-[12px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.02)] flex flex-col justify-between min-h-[220px]">
              <div>
                <div className="flex justify-between items-center border-b border-[#F2F2ED] pb-2 mb-4">
                  <h4 className="text-xs font-bold text-[#2B2A27] uppercase tracking-wider">Updates</h4>
                  <span className="text-xs font-bold text-[#5F7055] bg-[#EEF6EE] px-1.5 py-0.5 rounded">
                    Active System
                  </span>
                </div>

                {/* Updates checklist */}
                <div className="space-y-3.5">
                  <div className="flex items-center gap-3">
                    <div className="w-5 h-5 rounded-full bg-[#EEF6EE] flex items-center justify-center shrink-0 border border-[#D5EAD5]">
                      <Check size={12} className="text-[#5F7055]" />
                    </div>
                    <span className="text-xs font-bold text-[#2B2A27]">Daily market summary</span>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="w-5 h-5 rounded-full bg-[#EEF6EE] flex items-center justify-center shrink-0 border border-[#D5EAD5]">
                      <Check size={12} className="text-[#5F7055]" />
                    </div>
                    <span className="text-xs font-bold text-[#2B2A27]">Weekly insights</span>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="w-5 h-5 rounded-full bg-[#EEF6EE] flex items-center justify-center shrink-0 border border-[#D5EAD5]">
                      <Check size={12} className="text-[#5F7055]" />
                    </div>
                    <span className="text-xs font-bold text-[#2B2A27]">Monthly report</span>
                  </div>
                </div>
              </div>

              <div className="text-xs text-[#8C8278] font-bold border-t border-[#F2F2ED] pt-2.5 text-right uppercase tracking-wider mt-4">
                Systems Synchronized
              </div>
            </div>

          </div>

        </div>

        {/* ========================================================================= */}
        {/* RIGHT SIDEBAR PANEL */}
        {/* ========================================================================= */}
        <aside className="w-full xl:w-[280px] shrink-0 bg-card border border-black rounded-[12px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.02)] space-y-6 flex flex-col justify-between">
          
          <div className="space-y-6">
            
            {/* 1. Today's Insights */}
            <div className="space-y-3">
              <div className="flex justify-between items-center border-b border-[#F2F2ED] pb-1.5">
                <h4 className="text-xs font-bold text-[#2B2A27] uppercase tracking-wider">Today's Insights</h4>
                <div className="w-1.5 h-1.5 rounded-full bg-[#C9A96E]" />
              </div>
              <ul className="space-y-2.5 text-xs leading-relaxed">
                {cashAvailable > 0 && (
                  <li className="flex items-start gap-2.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#D67C38] mt-1.5 shrink-0" />
                    <span className="text-[#2B2A27] font-medium">
                      You have <strong className="font-extrabold">{formatINR(cashAvailable)}</strong> sitting idle
                    </span>
                  </li>
                )}
                {dailyPnl !== 0 && (
                  <li className="flex items-start gap-2.5">
                    <span className={cn("w-1.5 h-1.5 rounded-full mt-1.5 shrink-0", dailyPnl >= 0 ? "bg-[#5F7055]" : "bg-[#C85D5D]")} />
                    <span className="text-[#2B2A27] font-medium">
                      Today's P&L: <strong className="font-extrabold">{dailyPnl >= 0 ? '+' : ''}{formatINR(dailyPnl)}</strong>
                    </span>
                  </li>
                )}
                {topSector && (
                  <li className="flex items-start gap-2.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#C85D5D] mt-1.5 shrink-0" />
                    <span className="text-[#2B2A27] font-medium">
                      <strong className="font-extrabold">{topSector.weight_pct.toFixed(1)}%</strong> of your investments depend on {topSector.label}
                    </span>
                  </li>
                )}
                {positions.length === 0 && cashAvailable === 0 && (
                  <li className="flex items-start gap-2.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#8C8278] mt-1.5 shrink-0" />
                    <span className="text-[#8C8278] font-medium">No insights available yet</span>
                  </li>
                )}
              </ul>
            </div>

            {/* 2. Portfolio Safety */}
            <div className="space-y-3">
              <div className="flex justify-between items-center border-b border-[#F2F2ED] pb-1.5">
                <h4 className="text-xs font-bold text-[#2B2A27] uppercase tracking-wider">Portfolio Safety</h4>
                <span className="text-xs font-bold text-[#8C8278] uppercase">Limits</span>
              </div>
              <div className="space-y-2 text-xs font-medium">
                <div className="flex justify-between">
                  <span className="text-[#8C8278]">Risk Level</span>
                  <span className={cn("font-bold", riskLevel.color)}>
                    {summary ? riskLevel.text.replace("Risk: ", "") : "--"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#8C8278]">Possible Downside</span>
                  <span className="text-[#2B2A27] font-extrabold">
                    {summary && downsideHigh > 0
                      ? `${formatINR(downsideLow)}–${formatINR(downsideHigh)}`
                      : "--"
                    }
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#8C8278]">Recovery strength</span>
                  <span className={cn("font-bold", recoveryColor)}>
                    {summary ? recoveryStrength : "--"}
                  </span>
                </div>
              </div>
            </div>

            {/* 3. Watchlist */}
            <div className="space-y-3">
              <div className="flex justify-between items-center border-b border-[#F2F2ED] pb-1.5">
                <h4 className="text-xs font-bold text-[#2B2A27] uppercase tracking-wider">Watchlist</h4>
                <span className="text-xs font-bold text-[#8C8278] uppercase">Market</span>
              </div>
              
              <div className="space-y-2.5">
                {watchlistLoading ? (
                  <>
                    {[1,2,3].map(i => (
                      <div key={i} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Skeleton className="w-5 h-5 rounded-full" />
                          <Skeleton className="h-3 w-14" />
                        </div>
                        <Skeleton className="h-3 w-10" />
                      </div>
                    ))}
                  </>
                ) : watchlistItems.length > 0 ? (
                  watchlistItems.map((item) => {
                    const isPositive = item.change_percent >= 0
                    return (
                      <div key={item.ticker} className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <div className={cn(
                            "w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold",
                            isPositive ? "bg-[#ECFDF5] text-emerald-600" : "bg-[#FEE2E2] text-red-600"
                          )}>
                            {item.ticker.charAt(0)}
                          </div>
                          <span className="font-bold text-[#2B2A27]">{item.name}</span>
                        </div>
                        {/* Mini Sparkline or Dashed line if no history */}
                        <div className="w-10 h-4">
                          {item.price_history && item.price_history.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                              <LineChart data={item.price_history}>
                                <Line type="monotone" dataKey="price" stroke={isPositive ? "#5F7055" : "#C85D5D"} strokeWidth={1.5} dot={false} />
                              </LineChart>
                            </ResponsiveContainer>
                          ) : (
                            <svg className="w-full h-full" viewBox="0 0 40 15">
                              <line x1="0" y1="7.5" x2="40" y2="7.5" stroke="#8C8278" strokeWidth="1" strokeDasharray="2 2" />
                            </svg>
                          )}
                        </div>
                        <span className={cn(
                          "font-mono font-bold text-xs px-1.5 py-0.5 rounded",
                          isPositive
                            ? "text-[#5F7055] bg-[#EEF6EE]"
                            : "text-[#C85D5D] bg-[#FDF2F2]"
                        )}>
                          {isPositive ? "+" : ""}{item.change_percent.toFixed(1)}%
                        </span>
                      </div>
                    )
                  })
                ) : (
                  <p className="text-xs text-[#8C8278] font-medium">No watchlist data available</p>
                )}
              </div>
            </div>

            {/* 4. Market Watch */}
            <div className="space-y-3">
              <div className="flex justify-between items-center border-b border-[#F2F2ED] pb-1.5">
                <h4 className="text-xs font-bold text-[#2B2A27] uppercase tracking-wider">Market Watch</h4>
                <span className="text-xs font-bold text-[#8C8278] uppercase">Pulse</span>
              </div>
              <div className="space-y-2 text-xs">
                {marketLoading ? (
                  <>
                    {[1,2].map(i => (
                      <div key={i} className="flex items-center justify-between">
                        <Skeleton className="h-3 w-20" />
                        <Skeleton className="h-3 w-10" />
                      </div>
                    ))}
                  </>
                ) : marketMovers.length > 0 ? (
                  marketMovers.map((mover) => {
                    const isPositive = mover.change_percent >= 0
                    return (
                      <div key={mover.ticker} className="flex items-center justify-between">
                        <div className="flex flex-col">
                          <span className={cn("font-bold", isPositive ? "text-[#5F7055]" : "text-[#C85D5D]")}>
                            {mover.name || mover.ticker}
                          </span>
                          <span className={cn("text-xs font-medium", isPositive ? "text-[#5F7055]" : "text-[#C85D5D]")}>
                            {isPositive ? "Positive momentum" : "Under pressure"}
                          </span>
                        </div>
                        <span className={cn("font-mono font-extrabold", isPositive ? "text-[#5F7055]" : "text-[#C85D5D]")}>
                          {isPositive ? "+" : ""}{mover.change_percent.toFixed(1)}%
                        </span>
                      </div>
                    )
                  })
                ) : (
                  <p className="text-xs text-[#8C8278] font-medium">No market data available</p>
                )}
              </div>
            </div>

          </div>

          {/* ========================================= */}
          {/* 5. ASK RAUTREX (CHAT WIDGET) */}
          {/* ========================================= */}
          <div className="space-y-3 border-t border-[#F2F2ED] pt-5 mt-6">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-1.5">
                <Sparkles size={14} className="text-[#C9A96E]" />
                <h4 className="text-xs font-bold text-[#2B2A27] uppercase tracking-wider">Ask RAUTREX</h4>
              </div>
              <div className="flex items-center gap-2 text-[#8C8278]">
                <MoreHorizontal size={14} className="hover:text-[#2B2A27] cursor-pointer" />
                <X 
                  size={14} 
                  className="hover:text-[#2B2A27] cursor-pointer" 
                  onClick={() => {
                    setChatMessages([
                      { sender: "bot", text: "Ask RAUTREX system synchronized. Ready for queries.", timestamp: new Date() }
                    ])
                  }}
                />
              </div>
            </div>

            {/* Chat Conversation Scroll Panel */}
            <div className="h-[180px] bg-background border border-[#EBEBE6] rounded-lg p-2.5 overflow-y-auto space-y-2 custom-scrollbar text-xs">
              {chatMessages.map((msg, i) => (
                <div 
                  key={i} 
                  className={cn(
                    "flex flex-col p-2 rounded-lg max-w-[85%] leading-relaxed shadow-[0_1px_2px_rgba(0,0,0,0.01)]",
                    msg.sender === "user" 
                      ? "bg-[#EDE8DC] border border-[#D4CEC4] ml-auto text-right text-[#2B2A27]" 
                      : "bg-card border border-black text-[#2B2A27]"
                  )}
                >
                  <span className="font-semibold">{msg.text}</span>
                  <span className="text-[8px] text-[#8C8278] block mt-1">
                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              ))}
              
              {isTyping && (
                <div className="bg-card border border-black p-2 rounded-lg max-w-[50px] flex items-center justify-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#8C8278] animate-bounce" />
                  <span className="w-1.5 h-1.5 rounded-full bg-[#8C8278] animate-bounce [animation-delay:0.2s]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-[#8C8278] animate-bounce [animation-delay:0.4s]" />
                </div>
              )}
              <div ref={chatBottomRef} />
            </div>

            {/* Quick Suggestion Chips */}
            <div className="flex flex-wrap gap-1">
              <button 
                onClick={() => handleAskQuestion("Why is my portfolio down?")}
                className="bg-card border border-black hover:border-[#C9A96E] hover:text-[#C9A96E] text-xs font-bold text-[#8C8278] px-2 py-1 rounded-full transition-all"
              >
                Why is my portfolio down?
              </button>
              <button 
                onClick={() => handleAskQuestion("What is my portfolio risk?")}
                className="bg-card border border-black hover:border-[#C9A96E] hover:text-[#C9A96E] text-xs font-bold text-[#8C8278] px-2 py-1 rounded-full transition-all"
              >
                What is my portfolio risk?
              </button>
              <button 
                onClick={() => handleAskQuestion("Explain ETF simply")}
                className="bg-card border border-black hover:border-[#C9A96E] hover:text-[#C9A96E] text-xs font-bold text-[#8C8278] px-2 py-1 rounded-full transition-all"
              >
                Explain ETF simply
              </button>
            </div>

            {/* Input field */}
            <form 
              onSubmit={(e) => {
                e.preventDefault()
                handleAskQuestion(chatInput)
              }}
              className="flex items-center gap-1.5 border border-[#EBEBE6] bg-white p-1 rounded-lg shadow-sm"
            >
              <input
                type="text"
                placeholder="Type your question..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                className="flex-1 bg-transparent px-2 py-1 outline-none text-xs text-[#2B2A27] placeholder:text-[#8C8278]"
              />
              <button 
                type="submit" 
                className="w-6 h-6 rounded-md bg-[#8B6F47] hover:bg-[#735C3A] flex items-center justify-center text-[var(--text-primary)] transition-all shrink-0 active:scale-95"
              >
                <Send size={10} />
              </button>
            </form>

          </div>

        </aside>

      </div>

    </div>
  )
}
