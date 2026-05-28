"use client"

import { useEffect, useMemo, useState } from "react"
import {
  Activity,
  ArrowRightLeft,
  DollarSign,
  Layers,
  Plus,
  TrendingDown,
  TrendingUp,
  Wallet,
  X,
  MoreVertical,
  Trash2,
  Edit2,
  PieChart as PieChartIcon,
  LineChart,
  ChevronRight,
} from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useToast } from "@/components/ui/Toast"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { CardSurface } from "@/components/ui/CardSurface"
import { PanelSurface } from "@/components/ui/PanelSurface"
import { SectionHeader } from "@/components/ui/SectionHeader"
import { MetricCard } from "@/components/ui/MetricCard"
import { apiFetch } from "@/lib/api"
import { usePortfolioOverview } from "@/lib/use-portfolio-overview"
import { cn } from "@/lib/utils"

import AddAssetModal from "@/components/portfolios/AddAssetModal"
import DeletePortfolioModal from "@/components/portfolios/DeletePortfolioModal"
import ChartWrapper from '@/components/ChartWrapper';


const PIE_COLORS = ["#A67C52", "#D8CFC5", "#8A847D", "#5E5A56", "#2F6B3D", "#C2B8AD", "#EFE8DF"]
const STRATEGIES = ["Equity", "Growth", "Dividend", "Crypto", "Options"]


function formatPct(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined) return "—";
  return `${value >= 0 ? "+" : ""}${value.toFixed(digits)}%`
}


type TransactionType = "BUY" | "SELL" | "DEPOSIT" | "WITHDRAWAL" | "DIVIDEND" | "FEE"
type OptimizationResult = {
  metrics?: { return?: number; volatility?: number; sharpe?: number }
  random_portfolios?: Array<{ volatility: number; return: number }>
  frontier?: Array<{ volatility: number; return: number }>
  weight_details?: Array<{ ticker: string; weight: number }>
}

type RebalanceResult = {
  total_value?: number
  total_estimated_cost?: number
  trades?: Array<{ ticker: string; action: string; amount: number; shares: number; price: number }>
}

const getErrorMessage = (error: unknown, fallback: string) => (error instanceof Error ? error.message : fallback)


export default function PortfolioLab() {
  const { portfolios, overview, loading, error, selectedPortfolioId, setSelectedPortfolioId, refresh } = usePortfolioOverview()
  const { toast } = useToast()

  const [activeTab, setActiveTab] = useState("manager")
  const [isMounted, setIsMounted] = useState(false)
  const [activeCurrency, setActiveCurrency] = useState("USD")

  const formatCurrency = (value: number | null | undefined) => {
    if (value === null || value === undefined) return "—";
    return new Intl.NumberFormat(activeCurrency === "INR" ? "en-IN" : "en-US", {
      style: "currency",
      currency: activeCurrency,
      maximumFractionDigits: 0,
    }).format(value)
  }

  // Dynamically set currency based on active portfolio broker or holdings
  useEffect(() => {
    if (!overview) return
    const broker = overview?.portfolio?.broker?.toLowerCase()
    const isIndianBroker = broker === "upstox" || broker === "zerodha" || broker === "groww" || broker === "cas_statement"
    
    // Fallback: check if any holdings end with .NS or .BO (Indian exchanges)
    const hasIndianTicker = overview?.positions?.some(
      (pos: any) => pos.ticker && (pos.ticker.endsWith(".NS") || pos.ticker.endsWith(".BO"))
    )
    
    const dbCurrency = overview?.portfolio?.currency || overview?.portfolio?.base_currency
    const isINR = dbCurrency === "INR" || isIndianBroker || hasIndianTicker
    
    if (isINR) {
      setActiveCurrency("INR")
    } else {
      setActiveCurrency("USD")
    }
  }, [overview])
  
  useEffect(() => {
    setIsMounted(true)
  }, [])
  
  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showAddAssetModal, setShowAddAssetModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [showTransactionModal, setShowTransactionModal] = useState(false)
  
  // Form State
  const [portfolioName, setPortfolioName] = useState("")
  const [portfolioStrategy, setPortfolioStrategy] = useState("Equity")
  const [initialCash, setInitialCash] = useState("0")
  const [portfolioDescription, setPortfolioDescription] = useState("")
  
  const [transactionType, setTransactionType] = useState<TransactionType>("BUY")
  const [symbol, setSymbol] = useState("")
  const [quantity, setQuantity] = useState("")
  const [price, setPrice] = useState("")
  const [grossAmount, setGrossAmount] = useState("")
  const [transactionLoading, setTransactionLoading] = useState(false)

  // Optimization & Rebalance
  const [tickers, setTickers] = useState<string[]>([])
  const [newTicker, setNewTicker] = useState("")
  const [method, setMethod] = useState("markowitz")
  const [objective, setObjective] = useState("max_sharpe")
  const [optimizationLoading, setOptimizationLoading] = useState(false)
  const [optimizationResult, setOptimizationResult] = useState<OptimizationResult | null>(null)

  const [rebalanceLoading, setRebalanceLoading] = useState(false)
  const [rebalanceThreshold, setRebalanceThreshold] = useState(0.05)
  const [targetWeights, setTargetWeights] = useState<Record<string, number>>({})
  const [rebalanceResult, setRebalanceResult] = useState<RebalanceResult | null>(null)

  const positions = useMemo(() => overview?.positions || [], [overview?.positions])

  useEffect(() => {
    const symbols = positions.map((position) => position.ticker)
    if (symbols.length > 0) {
      setTickers((current) => (current.length > 0 ? current : symbols))
      setTargetWeights((current) => {
        if (Object.keys(current).length > 0) {
          return current
        }
        const next: Record<string, number> = {}
        positions.forEach((position) => {
          next[position.ticker] = position.weight_pct / 100
        })
        return next
      })
    }
  }, [positions])

  const summary = overview?.summary
  const allocation = overview?.allocation

  const yDomain = useMemo(() => {
    const curve = overview?.equity_curve || []
    const navValues = curve.map((d: any) => d.nav || 0)
    const minNav = navValues.length > 0 ? Math.min(...navValues) : 0
    const maxNav = navValues.length > 0 ? Math.max(...navValues) : 10000
    return [
      minNav > 0 ? minNav * 0.95 : 0,
      maxNav > 0 ? maxNav * 1.05 : 10000
    ]
  }, [overview?.equity_curve])

  const optimizedWeights = optimizationResult?.weight_details || []

  const rebalanceHoldings = useMemo(
    () =>
      positions.map((position) => ({
        ticker: position.ticker,
        shares: position.shares,
      })),
    [positions]
  )

  const handleCreatePortfolio = async () => {
    if (!portfolioName.trim()) return
    setTransactionLoading(true)
    try {
      await apiFetch("/users/me/portfolios", {
        method: "POST",
        body: JSON.stringify({ 
          name: portfolioName, 
          strategy: portfolioStrategy,
          initial_cash: Number(initialCash),
          description: portfolioDescription 
        }),
      })
      setPortfolioName("")
      setPortfolioStrategy("Equity")
      setInitialCash("0")
      setPortfolioDescription("")
      setShowCreateModal(false)
      await refresh()
      toast({ type: "success", title: "Portfolio created", description: "The new portfolio is ready." })
    } catch (err: unknown) {
      toast({ type: "error", title: "Create failed", description: getErrorMessage(err, "Create failed") })
    } finally {
      setTransactionLoading(false)
    }
  }

  const handleRecordTransaction = async () => {
    if (!overview?.portfolio?.id) return
    if ((transactionType === "BUY" || transactionType === "SELL") && (!symbol || !quantity || !price)) {
      toast({ type: "warning", title: "Missing fields", description: "Ticker, quantity, and price are required." })
      return
    }
    if (["DEPOSIT", "WITHDRAWAL", "DIVIDEND", "FEE"].includes(transactionType) && !grossAmount) {
      toast({ type: "warning", title: "Missing amount", description: "Cash amount is required for this transaction type." })
      return
    }

    setTransactionLoading(true)
    try {
      await apiFetch("/portfolio/transactions", {
        method: "POST",
        body: JSON.stringify({
          portfolio_id: overview.portfolio.id,
          transaction_type: transactionType,
          symbol: symbol || undefined,
          quantity: quantity ? Number(quantity) : undefined,
          price: price ? Number(price) : undefined,
          gross_amount: grossAmount ? Number(grossAmount) : undefined,
          fees: 0,
        }),
      })
      setShowTransactionModal(false)
      setSymbol("")
      setQuantity("")
      setPrice("")
      setGrossAmount("")
      await refresh()
      toast({ type: "success", title: "Transaction booked", description: `${transactionType} recorded successfully.` })
    } catch (err: unknown) {
      toast({ type: "error", title: "Transaction failed", description: getErrorMessage(err, "Transaction failed") })
    } finally {
      setTransactionLoading(false)
    }
  }

  const runOptimization = async () => {
    if (tickers.length === 0) {
      toast({ type: "warning", title: "No tickers", description: "Add at least one ticker to optimize." })
      return
    }
    setOptimizationLoading(true)
    try {
      const data = await apiFetch("/portfolio/optimize", {
        method: "POST",
        body: JSON.stringify({ tickers, method, objective }),
      })
      setOptimizationResult(data)
      toast({ type: "success", title: "Optimization complete", description: "Efficient frontier and weights updated." })
    } catch (err: unknown) {
      toast({ type: "error", title: "Optimization failed", description: getErrorMessage(err, "Optimization failed") })
    } finally {
      setOptimizationLoading(false)
    }
  }

  const runRebalance = async () => {
    if (positions.length === 0) {
      toast({ type: "warning", title: "No holdings", description: "Add positions before running rebalance analysis." })
      return
    }
    setRebalanceLoading(true)
    try {
      const data = await apiFetch("/portfolio/rebalance", {
        method: "POST",
        body: JSON.stringify({
          current_positions: rebalanceHoldings,
          target_weights: targetWeights,
          threshold: rebalanceThreshold,
          total_value: summary?.nav,
        }),
      })
      setRebalanceResult(data)
      toast({ type: "success", title: "Rebalance ready", description: "Trade list generated from current holdings." })
    } catch (err: unknown) {
      toast({ type: "error", title: "Rebalance failed", description: getErrorMessage(err, "Rebalance failed") })
    } finally {
      setRebalanceLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Activity className="text-accent animate-spin" size={32} />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto w-full pb-12">
      {/* Top Header Section */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
            <Layers className="text-accent" /> Portfolio Lab
          </h1>
          <p className="text-text-muted text-xs uppercase tracking-widest font-bold">Institutional Portfolio Management</p>
        </div>
        <div className="flex gap-2">
          <Button 
            onClick={() => setShowCreateModal(true)} 
            className="bg-accent hover:bg-accent/90 text-text-primary font-bold gap-2 px-6 h-11"
          >
            <Plus size={16} /> Create Portfolio
          </Button>
        </div>
      </div>

      {/* Portfolio Selector Cards */}
      {portfolios.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {portfolios.map((portfolio) => (
            <motion.div
              key={portfolio.id}
              whileHover={{ y: -2 }}
              onClick={() => setSelectedPortfolioId(portfolio.id)}
              className={cn(
                "relative cursor-pointer p-5 rounded-2xl border transition-all overflow-hidden group",
                selectedPortfolioId === portfolio.id 
                  ? "bg-accent/10 border-accent shadow-lg shadow-accent/10" 
                  : "bg-surface border-border hover:border-border-strong"
              )}
            >
              {selectedPortfolioId === portfolio.id && (
                <div className="absolute top-0 left-0 w-1 h-full bg-accent" />
              )}
              
              <div className="flex justify-between items-start mb-3">
                <div className="flex flex-col">
                  <h3 className={cn(
                    "font-bold text-sm transition-colors",
                    selectedPortfolioId === portfolio.id ? "text-accent" : "text-text-primary group-hover:text-accent"
                  )}>
                    {portfolio.name}
                  </h3>
                  <span className="text-[10px] text-text-muted font-mono uppercase">
                    {(portfolio as any).strategy || "Equity"}
                  </span>
                </div>
                
                <Popover>
                  <PopoverTrigger asChild>
                    <button 
                      onClick={(e) => e.stopPropagation()}
                      className="text-text-muted hover:text-text-primary transition-colors p-1"
                    >
                      <MoreVertical size={16} />
                    </button>
                  </PopoverTrigger>
                  <PopoverContent className="w-48 bg-surface border-border p-1" align="end" side="bottom">
                    <button 
                      className="w-full text-left px-3 py-2 text-xs text-text-primary hover:bg-card rounded-lg flex items-center gap-2"
                      onClick={(e) => {
                        e.stopPropagation();
                        // Edit functionality placeholder
                        toast({ type: "info", title: "Edit Portfolio", description: "Edit functionality coming soon." });
                      }}
                    >
                      <Edit2 size={14} className="text-text-muted" /> Edit Portfolio
                    </button>
                    <div className="h-[1px] bg-border my-1" />
                    <button 
                      className="w-full text-left px-3 py-2 text-xs text-negative hover:bg-negative/10 rounded-lg flex items-center gap-2"
                      onClick={(e) => {
                        e.stopPropagation();
                        setShowDeleteModal(true);
                      }}
                    >
                      <Trash2 size={14} /> Delete Portfolio
                    </button>
                  </PopoverContent>
                </Popover>
              </div>

              <div className="flex items-end justify-between mt-4">
                <div className="flex flex-col">
                  <span className="text-[10px] text-text-muted uppercase font-bold">Initial Cash</span>
                  <span className="text-sm font-mono text-text-primary">{formatCurrency((portfolio as any).cash_balance || 0)}</span>
                </div>
                <ChevronRight size={16} className={cn(
                  "transition-all",
                  selectedPortfolioId === portfolio.id ? "text-accent translate-x-0" : "text-text-secondary translate-x-[-4px] opacity-0 group-hover:opacity-100 group-hover:translate-x-0"
                )} />
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {error && (
        <CardSurface className="p-4 border-negative/20 bg-negative/5 text-sm text-negative">
          {error}
        </CardSurface>
      )}

      {!overview?.portfolio || !summary ? (
        <CardSurface className="p-12 flex flex-col items-center justify-center text-center space-y-6 min-h-[400px] border-dashed border-2 bg-card">
          <div className="w-16 h-16 bg-accent/10 rounded-full flex items-center justify-center">
            <Wallet className="text-accent" size={32} />
          </div>
          <div className="space-y-2">
            <h2 className="text-xl font-bold text-text-primary">No Portfolio Selected</h2>
            <p className="text-text-muted max-w-md mx-auto text-sm">
              Select or create a portfolio to view performance, manage holdings, and run institutional optimization.
            </p>
          </div>
          <Button onClick={() => setShowCreateModal(true)} className="bg-accent hover:bg-accent/90 text-text-primary font-bold h-11 px-8">
            <Plus size={16} className="mr-2" /> Create First Portfolio
          </Button>
        </CardSurface>
      ) : (
        <>
          {/* Action Buttons Row */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
               <h2 className="text-xl font-bold text-text-primary">{overview.portfolio.name} Dashboard</h2>
               <div className="px-3 py-1 bg-accent/10 border border-accent/20 rounded-full text-[10px] font-bold text-accent uppercase">
                 {(overview.portfolio as any).strategy || "Equity"}
               </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={() => setShowAddAssetModal(true)} className="bg-accent hover:bg-accent/90 text-text-primary font-bold gap-2 px-6 h-10">
                <Plus size={16} /> Add Asset
              </Button>
              <Button onClick={() => setShowTransactionModal(true)} variant="ghost" className="bg-card border border-border text-text-primary gap-2 h-10">
                <ArrowRightLeft size={16} /> Record Transaction
              </Button>
            </div>
          </div>

          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="bg-surface border border-border h-12 mb-4">
              <TabsTrigger value="manager" className="px-8 font-bold uppercase tracking-widest text-xs">Portfolio Manager</TabsTrigger>
              <TabsTrigger value="optimize" className="px-8 font-bold uppercase tracking-widest text-xs">Optimization Lab</TabsTrigger>
              <TabsTrigger value="rebalance" className="px-8 font-bold uppercase tracking-widest text-xs">Rebalancer</TabsTrigger>
            </TabsList>

            <TabsContent value="manager" className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-6 gap-4">
                <MetricCard 
                  title="NAV" 
                  value={formatCurrency(summary.nav)} 
                  icon={<Wallet className="text-accent" />} 
                />
                <MetricCard 
                  title="Cash Balance" 
                  value={formatCurrency(summary.cash)} 
                  icon={<DollarSign className="text-accent-teal" />} 
                />
                <MetricCard 
                  title="Daily P&L" 
                  value={formatCurrency(Math.abs(summary.daily_pnl))} 
                  icon={summary.daily_pnl >= 0 ? <TrendingUp className="text-positive" /> : <TrendingDown className="text-negative" />} 
                  change={formatPct(summary.daily_return_pct)} 
                  trend={summary.daily_pnl >= 0 ? "up" : "down"}
                />
                <MetricCard
                  title="Unrealized P&L"
                  value={formatCurrency(summary.unrealized_pnl_total || summary.unrealized_pnl)}
                  icon={<TrendingUp className="text-accent-teal" />}
                />

                <MetricCard 
                  title="Realized P&L" 
                  value={formatCurrency(summary.realized_pnl_total || summary.realized_pnl || 0)} 
                  icon={<ArrowRightLeft className="text-accent-teal" />} 
                />
                <MetricCard 
                  title="Holdings" 
                  value={summary.holdings_count.toString()} 
                  icon={<Layers className="text-text-primary" />} 
                />
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
                <CardSurface className="xl:col-span-8">
                  <div className="flex justify-between items-center mb-6">
                    <SectionHeader 
                      title="Equity Curve Analysis" 
                      description="Historical portfolio net asset value performance"
                      icon={<LineChart size={18} />}
                      className="mb-0"
                    />
                    <div className="text-right">
                      <p className="text-[10px] text-text-muted uppercase font-bold">YTD Performance</p>
                      <p className={cn("text-lg font-mono font-bold", summary.ytd_return_pct >= 0 ? "text-positive" : "text-negative")}>
                        {formatPct(summary.ytd_return_pct)}
                      </p>
                    </div>
                  </div>
                  <div className="h-[320px] w-full" style={{ minHeight: '320px' }}>
                    {isMounted ? (
                      <ChartWrapper height={300}>
                        <ResponsiveContainer width="100%" height="100%" aspect={2.5}>
                          <AreaChart data={overview.equity_curve}>
                            <defs>
                              <linearGradient id="portfolioEquity" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="var(--accent-teal)" stopOpacity={0.28} />
                                <stop offset="95%" stopColor="var(--accent-teal)" stopOpacity={0} />
                              </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                            <XAxis dataKey="snapshot_date" stroke="var(--text-muted)" fontSize={10} minTickGap={40} />
                            <YAxis stroke="var(--text-muted)" fontSize={10} domain={yDomain} tickFormatter={(value) => `${activeCurrency === "INR" ? "₹" : "$"}${value.toLocaleString()}`} />
                            <Tooltip formatter={(value: number) => formatCurrency(value)} contentStyle={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 16 }} />
                            <Area type="monotone" dataKey="nav" stroke="var(--accent-teal)" strokeWidth={2} fill="url(#portfolioEquity)" />
                          </AreaChart>
                        </ResponsiveContainer>
                      </ChartWrapper>
                    ) : (
                      <div className="w-full h-full bg-card animate-pulse rounded-xl" />
                    )}
                  </div>
                </CardSurface>

                <CardSurface className="xl:col-span-4">
                  <SectionHeader 
                    title="Sector Allocation" 
                    icon={<PieChartIcon size={18} />}
                  />
                  <div className="h-[260px] w-full" style={{ minHeight: '260px' }}>
                    {isMounted ? (
                      <ChartWrapper height={300}>
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie data={allocation?.by_sector || []} dataKey="value" nameKey="label" innerRadius={50} outerRadius={86} stroke="none">
                              {(allocation?.by_sector || []).map((_, index) => (
                                <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                              ))}
                            </Pie>
                            <Tooltip formatter={(value: number) => formatCurrency(value)} />
                          </PieChart>
                        </ResponsiveContainer>
                      </ChartWrapper>
                    ) : (
                      <div className="w-full h-full bg-card animate-pulse rounded-full" />
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-2 mt-4">
                    {(allocation?.by_sector || []).slice(0, 4).map((item, index) => (
                      <div key={item.label} className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: PIE_COLORS[index % PIE_COLORS.length] }} />
                        <span className="text-[10px] text-text-muted truncate">{item.label}</span>
                      </div>
                    ))}
                  </div>
                </CardSurface>
              </div>

              <CardSurface>
                <div className="flex justify-between items-center mb-6">
                  <SectionHeader 
                    title="Positions Book" 
                    description="Live portfolio holdings and real-time P&L"
                    className="mb-0"
                  />
                  <div className="text-right">
                    <p className="text-[10px] text-text-muted uppercase font-bold">Gross Exposure</p>
                    <p className="text-lg font-mono font-bold text-accent">{formatCurrency(summary.gross_exposure)}</p>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse font-mono text-sm">
                    <thead className="text-[10px] text-text-muted uppercase tracking-widest border-b border-border">
                      <tr>
                        <th className="px-3 py-3">Ticker</th>
                        <th className="px-3 py-3 text-right">Shares</th>
                        <th className="px-3 py-3 text-right">Avg Cost</th>
                        <th className="px-3 py-3 text-right">Live Price</th>
                        <th className="px-3 py-3 text-right">Market Value</th>
                        <th className="px-3 py-3 text-right">Unrealized</th>
                        <th className="px-3 py-3 text-right">Daily P&L</th>
                        <th className="px-3 py-3 text-right">Return %</th>
                        <th className="px-3 py-3 text-right">Weight %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {positions.length > 0 ? (
                        positions.map((position) => (
                          <tr key={position.ticker} className="border-b border-border hover:bg-card">
                            <td className="px-3 py-4">
                              <div className="flex flex-col">
                                <span className="font-bold text-text-primary">{position.ticker}</span>
                                <span className="text-[10px] text-text-muted uppercase">{position.sector || position.asset_type}</span>
                              </div>
                            </td>
                            <td className="px-3 py-4 text-right text-text-secondary">{position.shares.toFixed(4).replace(/\.?0+$/, "")}</td>
                            <td className="px-3 py-4 text-right text-text-secondary">{formatCurrency(position.avg_cost_per_share)}</td>
                            <td className="px-3 py-4 text-right text-text-primary">{formatCurrency(position.live_price)}</td>
                            <td className="px-3 py-4 text-right text-text-primary">{formatCurrency(position.market_value)}</td>
                            <td className={cn("px-3 py-4 text-right font-bold", position.unrealized_pnl >= 0 ? "text-positive" : "text-negative")}>{formatCurrency(position.unrealized_pnl)}</td>
                            <td className={cn("px-3 py-4 text-right font-bold", position.daily_pnl >= 0 ? "text-positive" : "text-negative")}>{formatCurrency(position.daily_pnl)}</td>
                            <td className={cn("px-3 py-4 text-right font-bold", position.total_return_pct >= 0 ? "text-positive" : "text-negative")}>{formatPct(position.total_return_pct)}</td>
                            <td className="px-3 py-4 text-right text-accent">{position.weight_pct.toFixed(2)}%</td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={10} className="px-3 py-12 text-center text-text-muted italic">
                            No holdings in this portfolio. Use the "Add Asset" button to get started.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </CardSurface>
            </TabsContent>

            <TabsContent value="optimize" className="space-y-6">
              <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
                <CardSurface className="xl:col-span-4 space-y-6">
                  <div className="space-y-3">
                    <Label className="text-[10px] uppercase tracking-widest text-text-muted font-bold">Universe</Label>
                    <div className="flex flex-wrap gap-2">
                      {tickers.map((ticker) => (
                        <button key={ticker} onClick={() => setTickers((current) => current.filter((item) => item !== ticker))} className="px-3 py-1 rounded-full bg-card border border-border text-xs font-mono text-text-primary flex items-center gap-2">
                          {ticker} <X size={12} />
                        </button>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <Input value={newTicker} onChange={(event) => setNewTicker(event.target.value.toUpperCase())} placeholder="AAPL" className="bg-surface h-10 border-border" />
                      <Button onClick={() => {
                        if (!newTicker || tickers.includes(newTicker)) return
                        setTickers((current) => [...current, newTicker])
                        setNewTicker("")
                      }} className="bg-accent hover:bg-accent/90 text-text-primary">Add</Button>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <Label className="text-[10px] uppercase tracking-widest text-text-muted font-bold">Method</Label>
                    <div className="grid grid-cols-1 gap-2">
                      {[
                        { id: "markowitz", label: "Mean-Variance" },
                        { id: "risk_parity", label: "Risk Parity" },
                        { id: "max_diversification", label: "Max Diversification" },
                      ].map((option) => (
                        <button key={option.id} onClick={() => setMethod(option.id)} className={cn("p-3 rounded-xl border text-left transition-all", method === option.id ? "border-accent bg-accent/10 text-text-primary" : "border-border bg-surface text-text-muted")}>
                          <p className="text-xs font-bold uppercase">{option.label}</p>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-3">
                    <Label className="text-[10px] uppercase tracking-widest text-text-muted font-bold">Objective</Label>
                    <select value={objective} onChange={(event) => setObjective(event.target.value)} className="w-full bg-surface border border-border rounded-xl h-11 px-4 text-sm text-text-primary">
                      <option value="max_sharpe">Max Sharpe</option>
                      <option value="min_vol">Min Volatility</option>
                      <option value="max_return">Max Return</option>
                    </select>
                  </div>

                  <Button onClick={runOptimization} loading={optimizationLoading} className="w-full bg-accent hover:bg-accent/90 text-text-primary font-bold h-11">
                    Run Optimization
                  </Button>
                </CardSurface>

                <CardSurface className="xl:col-span-8 min-h-[520px]">
                  {optimizationResult ? (
                    <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 h-full">
                      <div className="xl:col-span-8 h-[420px]" style={{ minHeight: '420px' }}>
                        {isMounted ? (
                          <ChartWrapper height={300}>
                            <ResponsiveContainer width="100%" height="100%">
                              <ScatterChart>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                                <XAxis type="number" dataKey="volatility" stroke="var(--text-muted)" tickFormatter={(value) => `${(value * 100).toFixed(1)}%`} />
                                <YAxis type="number" dataKey="return" stroke="var(--text-muted)" tickFormatter={(value) => `${(value * 100).toFixed(1)}%`} />
                                <Tooltip formatter={(value: number) => `${(value * 100).toFixed(2)}%`} contentStyle={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 16 }} />
                                <Scatter data={optimizationResult.random_portfolios || []} fill="var(--border-strong)" />
                                <Scatter data={optimizationResult.frontier || []} fill="var(--accent-teal)" />
                              </ScatterChart>
                            </ResponsiveContainer>
                          </ChartWrapper>
                        ) : (
                          <div className="w-full h-full bg-card animate-pulse rounded-2xl" />
                        )}
                      </div>
                      <div className="xl:col-span-4 space-y-4">
                        <MetricCard title="Expected Return" value={formatPct((optimizationResult.metrics?.return || 0) * 100)} icon={<TrendingUp className="text-positive" />} trend="up" change={((optimizationResult.metrics?.return || 0) * 100).toFixed(2) + "%"} />
                        <MetricCard title="Volatility" value={formatPct((optimizationResult.metrics?.volatility || 0) * 100)} icon={<TrendingDown className="text-negative" />} trend="down" change={((optimizationResult.metrics?.volatility || 0) * 100).toFixed(2) + "%"} />
                        <MetricCard title="Sharpe Ratio" value={(optimizationResult.metrics?.sharpe || 0).toFixed(2)} icon={<Activity className="text-accent" />} />
                        <div className="p-4 rounded-xl bg-card border border-border space-y-3">
                          {optimizedWeights.map((weight, index: number) => (
                            <div key={weight.ticker} className="flex justify-between items-center text-xs font-mono">
                              <div className="flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: PIE_COLORS[index % PIE_COLORS.length] }} />
                                <span className="text-text-primary">{weight.ticker}</span>
                              </div>
                              <span className="text-accent">{((weight.weight || 0) * 100).toFixed(1)}%</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="h-full flex items-center justify-center text-center text-text-muted">
                      Run optimization to generate institutional weights and frontier analytics.
                    </div>
                  )}
                </CardSurface>
              </div>
            </TabsContent>

            <TabsContent value="rebalance" className="space-y-6">
              <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
                <CardSurface className="xl:col-span-4 space-y-5">
                  <div className="space-y-3">
                    <Label className="text-[10px] uppercase tracking-widest text-text-muted font-bold">Target Weights</Label>
                    {positions.map((position) => (
                      <div key={position.ticker} className="flex items-center justify-between gap-3">
                        <span className="text-sm font-mono text-text-primary">{position.ticker}</span>
                        <Input
                          type="number"
                          value={((targetWeights[position.ticker] || 0) * 100).toFixed(2)}
                          onChange={(event) =>
                            setTargetWeights((current) => ({
                              ...current,
                              [position.ticker]: Number(event.target.value) / 100,
                            }))
                          }
                          className="w-24 bg-surface border-border h-9 text-right"
                        />
                      </div>
                    ))}
                  </div>
                  <div className="space-y-3">
                    <Label className="text-[10px] uppercase tracking-widest text-text-muted font-bold">Drift Threshold: {(rebalanceThreshold * 100).toFixed(0)}%</Label>
                    <input type="range" min="0" max="0.2" step="0.01" value={rebalanceThreshold} onChange={(event) => setRebalanceThreshold(Number(event.target.value))} className="w-full accent-accent" />
                  </div>
                  <Button onClick={runRebalance} loading={rebalanceLoading} className="w-full bg-accent hover:bg-accent/90 text-text-primary font-bold h-11">
                    Analyze Rebalance
                  </Button>
                </CardSurface>

                <CardSurface className="xl:col-span-8">
                  {rebalanceResult ? (
                    <div className="space-y-6">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <MetricCard title="Total Value" value={formatCurrency(rebalanceResult.total_value || 0)} icon={<Wallet className="text-accent" />} />
                        <MetricCard title="Trades Needed" value={String((rebalanceResult.trades || []).length)} icon={<ArrowRightLeft className="text-text-primary" />} />
                        <MetricCard title="Estimated Cost" value={formatCurrency(rebalanceResult.total_estimated_cost || 0)} icon={<DollarSign className="text-accent-teal" />} />
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse font-mono text-sm">
                          <thead className="text-[10px] text-text-muted uppercase tracking-widest border-b border-border">
                            <tr>
                              <th className="px-3 py-3">Ticker</th>
                              <th className="px-3 py-3 text-right">Action</th>
                              <th className="px-3 py-3 text-right">Amount</th>
                              <th className="px-3 py-3 text-right">Shares</th>
                              <th className="px-3 py-3 text-right">Price</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(rebalanceResult.trades || []).map((trade) => (
                              <tr key={`${trade.ticker}-${trade.action}`} className="border-b border-border hover:bg-card">
                                <td className="px-3 py-4 text-text-primary font-bold">{trade.ticker}</td>
                                <td className={cn("px-3 py-4 text-right font-bold", trade.action === "BUY" ? "text-positive" : "text-negative")}>{trade.action}</td>
                                <td className="px-3 py-4 text-right text-text-primary">{formatCurrency(trade.amount)}</td>
                                <td className="px-3 py-4 text-right text-text-secondary">{Number(trade.shares || 0).toFixed(4).replace(/\.?0+$/, "")}</td>
                                <td className="px-3 py-4 text-right text-text-secondary">{formatCurrency(trade.price)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ) : (
                    <div className="h-full min-h-[320px] flex items-center justify-center text-center text-text-muted">
                      Rebalance analysis will generate drift-aware trade instructions from your live holdings.
                    </div>
                  )}
                </CardSurface>
              </div>
            </TabsContent>
          </Tabs>
        </>
      )}

      {/* Modals */}
      <AnimatePresence>
        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShowCreateModal(false)} className="absolute inset-0 bg-background/60 backdrop-blur-sm" />
            <motion.div initial={{ scale: 0.92, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.92, opacity: 0 }} className="relative w-full max-w-md">
              <CardSurface className="p-8 rounded-3xl shadow-2xl">
                <h2 className="text-2xl font-bold text-text-primary mb-6">Create Portfolio</h2>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label className="text-xs uppercase font-bold text-text-muted">Portfolio Name</Label>
                    <Input value={portfolioName} onChange={(event) => setPortfolioName(event.target.value)} placeholder="Main Equity / Growth" className="bg-surface border-border h-12 text-text-primary" />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label className="text-xs uppercase font-bold text-text-muted">Strategy Type</Label>
                      <select 
                        value={portfolioStrategy} 
                        onChange={(event) => setPortfolioStrategy(event.target.value)} 
                        className="w-full bg-surface border border-border rounded-xl h-12 px-4 text-sm text-text-primary"
                      >
                        {STRATEGIES.map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs uppercase font-bold text-text-muted">Initial Cash</Label>
                      <Input 
                        type="number" 
                        value={initialCash} 
                        onChange={(event) => setInitialCash(event.target.value)} 
                        className="bg-surface border-border h-12 text-text-primary" 
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-xs uppercase font-bold text-text-muted">Description</Label>
                    <Input value={portfolioDescription} onChange={(event) => setPortfolioDescription(event.target.value)} placeholder="Institutional long-only mandate" className="bg-surface border-border h-12 text-text-primary" />
                  </div>
                  
                  <div className="flex gap-3 pt-4">
                    <Button variant="ghost" onClick={() => setShowCreateModal(false)} className="flex-1 h-12 font-bold text-text-muted hover:text-text-primary">Cancel</Button>
                    <Button onClick={handleCreatePortfolio} loading={transactionLoading} className="flex-1 h-12 bg-accent hover:bg-accent/90 text-text-primary font-bold">Create</Button>
                  </div>
                </div>
              </CardSurface>
            </motion.div>
          </div>
        )}

        {showTransactionModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShowTransactionModal(false)} className="absolute inset-0 bg-background/60 backdrop-blur-sm" />
            <motion.div initial={{ scale: 0.92, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.92, opacity: 0 }} className="relative w-full max-lg">
              <CardSurface className="p-8 rounded-3xl shadow-2xl">
                <h2 className="text-2xl font-bold text-text-primary mb-6">Record Transaction</h2>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label className="text-xs uppercase font-bold text-text-muted">Transaction Type</Label>
                    <select value={transactionType} onChange={(event) => setTransactionType(event.target.value as TransactionType)} className="w-full bg-surface border border-border rounded-xl h-12 px-4 text-sm text-text-primary">
                      {["BUY", "SELL", "DEPOSIT", "WITHDRAWAL", "DIVIDEND", "FEE"].map((type) => (
                        <option key={type} value={type}>{type}</option>
                      ))}
                    </select>
                  </div>
                  {(transactionType === "BUY" || transactionType === "SELL") && (
                    <>
                      <div className="grid grid-cols-3 gap-3">
                        <div className="col-span-1 space-y-2">
                          <Label className="text-xs uppercase font-bold text-text-muted">Ticker</Label>
                          <Input value={symbol} onChange={(event) => setSymbol(event.target.value.toUpperCase())} placeholder="NVDA" className="bg-surface border-border h-12 text-text-primary" />
                        </div>
                        <div className="space-y-2">
                          <Label className="text-xs uppercase font-bold text-text-muted">Shares</Label>
                          <Input type="number" value={quantity} onChange={(event) => setQuantity(event.target.value)} className="bg-surface border-border h-12 text-text-primary" />
                        </div>
                        <div className="space-y-2">
                          <Label className="text-xs uppercase font-bold text-text-muted">Price</Label>
                          <Input type="number" value={price} onChange={(event) => setPrice(event.target.value)} className="bg-surface border-border h-12 text-text-primary" />
                        </div>
                      </div>
                    </>
                  )}
                  {["DEPOSIT", "WITHDRAWAL", "DIVIDEND", "FEE"].includes(transactionType) && (
                    <div className="space-y-2">
                      <Label className="text-xs uppercase font-bold text-text-muted">Cash Amount</Label>
                      <Input type="number" value={grossAmount} onChange={(event) => setGrossAmount(event.target.value)} className="bg-surface border-border h-12 text-text-primary" />
                    </div>
                  )}
                  <div className="flex gap-3 pt-4">
                    <Button variant="ghost" onClick={() => setShowTransactionModal(false)} className="flex-1 h-12 font-bold text-text-muted hover:text-text-primary">Cancel</Button>
                    <Button onClick={handleRecordTransaction} loading={transactionLoading} className="flex-1 h-12 bg-accent hover:bg-accent/90 text-text-primary font-bold">Save</Button>
                  </div>
                </div>
              </CardSurface>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {overview?.portfolio && (
        <>
          <AddAssetModal
            isOpen={showAddAssetModal}
            onClose={() => setShowAddAssetModal(false)}
            portfolioId={overview.portfolio.id}
            onSuccess={refresh}
          />
          <DeletePortfolioModal
            isOpen={showDeleteModal}
            onClose={() => setShowDeleteModal(false)}
            portfolioId={overview.portfolio.id}
            portfolioName={overview.portfolio.name}
            onSuccess={refresh}
          />
        </>
      )}
    </div>
  )}
