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

import MetricCard from "@/components/metric-card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useToast } from "@/components/ui/Toast"
import { apiFetch } from "@/lib/api"
import { usePortfolioOverview } from "@/lib/use-portfolio-overview"
import { cn } from "@/lib/utils"


const PIE_COLORS = ["#00d4ff", "#10b981", "#f59e0b", "#7c3aed", "#f43f5e", "#6366f1", "#22c55e", "#a855f7"]


function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value || 0)
}


function formatPct(value: number, digits = 2) {
  const normalized = value || 0
  return `${normalized >= 0 ? "+" : ""}${normalized.toFixed(digits)}%`
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
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showTransactionModal, setShowTransactionModal] = useState(false)
  const [portfolioName, setPortfolioName] = useState("")
  const [portfolioDescription, setPortfolioDescription] = useState("")
  const [transactionType, setTransactionType] = useState<TransactionType>("BUY")
  const [symbol, setSymbol] = useState("")
  const [quantity, setQuantity] = useState("")
  const [price, setPrice] = useState("")
  const [grossAmount, setGrossAmount] = useState("")
  const [transactionLoading, setTransactionLoading] = useState(false)

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
        body: JSON.stringify({ name: portfolioName, description: portfolioDescription }),
      })
      setPortfolioName("")
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
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Layers className="text-accent" /> Portfolio Lab
          </h1>
          {portfolios.length > 0 && (
            <div className="flex bg-surface border border-white/5 p-1 rounded-xl gap-1 overflow-x-auto">
              {portfolios.map((portfolio) => (
                <button
                  key={portfolio.id}
                  onClick={() => setSelectedPortfolioId(portfolio.id)}
                  className={cn(
                    "px-4 py-1.5 rounded-lg text-[10px] font-bold uppercase transition-all whitespace-nowrap",
                    selectedPortfolioId === portfolio.id ? "bg-accent text-black" : "text-gray-500 hover:text-white"
                  )}
                >
                  {portfolio.name}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="flex gap-2">
          <Button onClick={() => setShowTransactionModal(true)} className="bg-white/5 border border-white/10 text-white gap-2">
            <ArrowRightLeft size={16} /> Record Transaction
          </Button>
          <Button onClick={() => setShowCreateModal(true)} className="bg-accent hover:bg-accent/90 text-black font-bold gap-2 px-6">
            <Plus size={16} /> Create Portfolio
          </Button>
        </div>
      </div>

      {error && (
        <div className="glass-panel p-4 rounded-2xl border border-red-500/20 bg-red-500/5 text-sm text-red-300">
          {error}
        </div>
      )}

      {!overview?.portfolio || !summary ? (
        <div className="glass-panel p-12 rounded-2xl flex flex-col items-center justify-center text-center space-y-6 min-h-[400px] border-dashed border-2 border-white/5 bg-white/[0.01]">
          <div className="w-16 h-16 bg-accent/10 rounded-full flex items-center justify-center">
            <Wallet className="text-accent" size={32} />
          </div>
          <div className="space-y-2">
            <h2 className="text-xl font-bold text-white">No Portfolio Found</h2>
            <p className="text-gray-500 max-w-md mx-auto text-sm">
              Create a portfolio and start recording deposits, buys, sells, and fees to build a real institutional book.
            </p>
          </div>
        </div>
      ) : (
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-surface border border-white/5 h-12 mb-4">
            <TabsTrigger value="manager" className="px-8 font-bold uppercase tracking-widest text-xs">Portfolio Manager</TabsTrigger>
            <TabsTrigger value="optimize" className="px-8 font-bold uppercase tracking-widest text-xs">Optimization Lab</TabsTrigger>
            <TabsTrigger value="rebalance" className="px-8 font-bold uppercase tracking-widest text-xs">Rebalancer</TabsTrigger>
          </TabsList>

          <TabsContent value="manager" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-6 gap-4">
              <MetricCard title="NAV" value={formatCurrency(summary.nav)} icon={<Wallet className="text-accent" />} />
              <MetricCard title="Cash" value={formatCurrency(summary.cash)} icon={<DollarSign className="text-amber-400" />} />
              <MetricCard title="Daily P&L" value={formatCurrency(summary.daily_pnl)} icon={summary.daily_pnl >= 0 ? <TrendingUp className="text-green-500" /> : <TrendingDown className="text-red-500" />} trend={formatPct(summary.daily_return_pct)} trendColor={summary.daily_pnl >= 0 ? "text-green-500" : "text-red-500"} />
              <MetricCard title="Unrealized" value={formatCurrency(summary.unrealized_pnl)} icon={<TrendingUp className="text-cyan-400" />} />
              <MetricCard title="Realized" value={formatCurrency(summary.realized_pnl_total || summary.realized_pnl || 0)} icon={<ArrowRightLeft className="text-purple-400" />} />
              <MetricCard title="Holdings" value={summary.holdings_count.toString()} icon={<Layers className="text-white" />} />
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
              <div className="xl:col-span-8 glass-panel p-6 rounded-2xl bg-[#0d0d14]">
                <div className="flex justify-between items-center mb-6">
                  <div>
                    <p className="text-[10px] text-gray-500 uppercase tracking-[0.2em] font-bold">Historical Equity</p>
                    <h3 className="text-lg font-bold text-white">Daily snapshots from transaction history</h3>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] text-gray-500 uppercase font-bold">YTD</p>
                    <p className={cn("text-lg font-mono font-bold", summary.ytd_return_pct >= 0 ? "text-green-400" : "text-red-400")}>
                      {formatPct(summary.ytd_return_pct)}
                    </p>
                  </div>
                </div>
                <ResponsiveContainer width="100%" height={320}>
                  <AreaChart data={overview.equity_curve}>
                    <defs>
                      <linearGradient id="portfolioEquity" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.28} />
                        <stop offset="95%" stopColor="#00d4ff" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis dataKey="snapshot_date" stroke="rgba(255,255,255,0.35)" fontSize={10} minTickGap={40} />
                    <YAxis stroke="rgba(255,255,255,0.35)" fontSize={10} tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`} />
                    <Tooltip formatter={(value: number) => formatCurrency(value)} contentStyle={{ backgroundColor: "#11121a", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 16 }} />
                    <Area type="monotone" dataKey="nav" stroke="#00d4ff" strokeWidth={2} fill="url(#portfolioEquity)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              <div className="xl:col-span-4 glass-panel p-6 rounded-2xl bg-[#0d0d14]">
                <h3 className="text-lg font-bold text-white mb-4">Sector Allocation</h3>
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Pie data={allocation?.by_sector || []} dataKey="value" nameKey="label" innerRadius={50} outerRadius={86} stroke="none">
                      {(allocation?.by_sector || []).map((_, index) => (
                        <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value: number) => formatCurrency(value)} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="glass-panel p-6 rounded-2xl bg-[#0d0d14]">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <p className="text-[10px] text-gray-500 uppercase tracking-[0.2em] font-bold">Live Book</p>
                  <h3 className="text-lg font-bold text-white">Current positions</h3>
                </div>
                <div className="text-right">
                  <p className="text-[10px] text-gray-500 uppercase font-bold">Gross Exposure</p>
                  <p className="text-lg font-mono font-bold text-accent">{formatCurrency(summary.gross_exposure)}</p>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse font-mono text-sm">
                  <thead className="text-[10px] text-gray-500 uppercase tracking-widest border-b border-white/5">
                    <tr>
                      <th className="px-3 py-3">Ticker</th>
                      <th className="px-3 py-3 text-right">Shares</th>
                      <th className="px-3 py-3 text-right">Avg Cost</th>
                      <th className="px-3 py-3 text-right">Live Price</th>
                      <th className="px-3 py-3 text-right">Cost Basis</th>
                      <th className="px-3 py-3 text-right">Market Value</th>
                      <th className="px-3 py-3 text-right">Unrealized</th>
                      <th className="px-3 py-3 text-right">Daily P&L</th>
                      <th className="px-3 py-3 text-right">Return %</th>
                      <th className="px-3 py-3 text-right">Weight %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map((position) => (
                      <tr key={position.ticker} className="border-b border-white/5 hover:bg-white/[0.02]">
                        <td className="px-3 py-4">
                          <div className="flex flex-col">
                            <span className="font-bold text-white">{position.ticker}</span>
                            <span className="text-[10px] text-gray-500 uppercase">{position.sector || position.asset_type}</span>
                          </div>
                        </td>
                        <td className="px-3 py-4 text-right text-gray-300">{position.shares.toFixed(4).replace(/\.?0+$/, "")}</td>
                        <td className="px-3 py-4 text-right text-gray-300">{formatCurrency(position.avg_cost_per_share)}</td>
                        <td className="px-3 py-4 text-right text-white">{formatCurrency(position.live_price)}</td>
                        <td className="px-3 py-4 text-right text-gray-300">{formatCurrency(position.cost_basis)}</td>
                        <td className="px-3 py-4 text-right text-white">{formatCurrency(position.market_value)}</td>
                        <td className={cn("px-3 py-4 text-right font-bold", position.unrealized_pnl >= 0 ? "text-green-400" : "text-red-400")}>{formatCurrency(position.unrealized_pnl)}</td>
                        <td className={cn("px-3 py-4 text-right font-bold", position.daily_pnl >= 0 ? "text-green-400" : "text-red-400")}>{formatCurrency(position.daily_pnl)}</td>
                        <td className={cn("px-3 py-4 text-right font-bold", position.total_return_pct >= 0 ? "text-green-400" : "text-red-400")}>{formatPct(position.total_return_pct)}</td>
                        <td className="px-3 py-4 text-right text-accent">{position.weight_pct.toFixed(2)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="optimize" className="space-y-6">
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
              <div className="xl:col-span-4 glass-panel p-6 rounded-2xl bg-[#0d0d14] space-y-6">
                <div className="space-y-3">
                  <Label className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">Universe</Label>
                  <div className="flex flex-wrap gap-2">
                    {tickers.map((ticker) => (
                      <button key={ticker} onClick={() => setTickers((current) => current.filter((item) => item !== ticker))} className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-mono text-white flex items-center gap-2">
                        {ticker} <X size={12} />
                      </button>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Input value={newTicker} onChange={(event) => setNewTicker(event.target.value.toUpperCase())} placeholder="AAPL" className="bg-surface h-10" />
                    <Button onClick={() => {
                      if (!newTicker || tickers.includes(newTicker)) return
                      setTickers((current) => [...current, newTicker])
                      setNewTicker("")
                    }} className="bg-accent hover:bg-accent/90 text-black">Add</Button>
                  </div>
                </div>

                <div className="space-y-3">
                  <Label className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">Method</Label>
                  <div className="grid grid-cols-1 gap-2">
                    {[
                      { id: "markowitz", label: "Mean-Variance" },
                      { id: "risk_parity", label: "Risk Parity" },
                      { id: "max_diversification", label: "Max Diversification" },
                    ].map((option) => (
                      <button key={option.id} onClick={() => setMethod(option.id)} className={cn("p-3 rounded-xl border text-left transition-all", method === option.id ? "border-accent bg-accent/10 text-white" : "border-white/5 bg-surface text-gray-400")}>
                        <p className="text-xs font-bold uppercase">{option.label}</p>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-3">
                  <Label className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">Objective</Label>
                  <select value={objective} onChange={(event) => setObjective(event.target.value)} className="w-full bg-surface border border-white/5 rounded-xl h-11 px-4 text-sm text-white">
                    <option value="max_sharpe">Max Sharpe</option>
                    <option value="min_vol">Min Volatility</option>
                    <option value="max_return">Max Return</option>
                  </select>
                </div>

                <Button onClick={runOptimization} loading={optimizationLoading} className="w-full bg-accent hover:bg-accent/90 text-black font-bold h-11">
                  Run Optimization
                </Button>
              </div>

              <div className="xl:col-span-8 glass-panel p-6 rounded-2xl bg-[#0d0d14] min-h-[520px]">
                {optimizationResult ? (
                  <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 h-full">
                    <div className="xl:col-span-8 h-[420px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <ScatterChart>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                          <XAxis type="number" dataKey="volatility" stroke="rgba(255,255,255,0.35)" tickFormatter={(value) => `${(value * 100).toFixed(1)}%`} />
                          <YAxis type="number" dataKey="return" stroke="rgba(255,255,255,0.35)" tickFormatter={(value) => `${(value * 100).toFixed(1)}%`} />
                          <Tooltip formatter={(value: number) => `${(value * 100).toFixed(2)}%`} contentStyle={{ backgroundColor: "#11121a", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 16 }} />
                          <Scatter data={optimizationResult.random_portfolios || []} fill="rgba(255,255,255,0.12)" />
                          <Scatter data={optimizationResult.frontier || []} fill="#00d4ff" />
                        </ScatterChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="xl:col-span-4 space-y-4">
                      <MetricCard title="Expected Return" value={formatPct((optimizationResult.metrics?.return || 0) * 100)} icon={<TrendingUp className="text-green-400" />} />
                      <MetricCard title="Volatility" value={formatPct((optimizationResult.metrics?.volatility || 0) * 100)} icon={<TrendingDown className="text-red-400" />} />
                      <MetricCard title="Sharpe" value={(optimizationResult.metrics?.sharpe || 0).toFixed(2)} icon={<Activity className="text-accent" />} />
                      <div className="glass-panel p-4 rounded-xl bg-surface border border-white/5 space-y-3">
                        {optimizedWeights.map((weight, index: number) => (
                          <div key={weight.ticker} className="flex justify-between items-center text-xs font-mono">
                            <div className="flex items-center gap-2">
                              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: PIE_COLORS[index % PIE_COLORS.length] }} />
                              <span className="text-white">{weight.ticker}</span>
                            </div>
                            <span className="text-accent">{((weight.weight || 0) * 100).toFixed(1)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="h-full flex items-center justify-center text-center text-gray-500">
                    Run optimization to generate institutional weights and frontier analytics.
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="rebalance" className="space-y-6">
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
              <div className="xl:col-span-4 glass-panel p-6 rounded-2xl bg-[#0d0d14] space-y-5">
                <div className="space-y-3">
                  <Label className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">Target Weights</Label>
                  {positions.map((position) => (
                    <div key={position.ticker} className="flex items-center justify-between gap-3">
                      <span className="text-sm font-mono text-white">{position.ticker}</span>
                      <Input
                        type="number"
                        value={((targetWeights[position.ticker] || 0) * 100).toFixed(2)}
                        onChange={(event) =>
                          setTargetWeights((current) => ({
                            ...current,
                            [position.ticker]: Number(event.target.value) / 100,
                          }))
                        }
                        className="w-24 bg-surface h-9 text-right"
                      />
                    </div>
                  ))}
                </div>
                <div className="space-y-3">
                  <Label className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">Drift Threshold: {(rebalanceThreshold * 100).toFixed(0)}%</Label>
                  <input type="range" min="0" max="0.2" step="0.01" value={rebalanceThreshold} onChange={(event) => setRebalanceThreshold(Number(event.target.value))} className="w-full accent-accent" />
                </div>
                <Button onClick={runRebalance} loading={rebalanceLoading} className="w-full bg-accent hover:bg-accent/90 text-black font-bold h-11">
                  Analyze Rebalance
                </Button>
              </div>

              <div className="xl:col-span-8 glass-panel p-6 rounded-2xl bg-[#0d0d14]">
                {rebalanceResult ? (
                  <div className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <MetricCard title="Total Value" value={formatCurrency(rebalanceResult.total_value || 0)} icon={<Wallet className="text-accent" />} />
                      <MetricCard title="Trades Needed" value={String((rebalanceResult.trades || []).length)} icon={<ArrowRightLeft className="text-white" />} />
                      <MetricCard title="Estimated Cost" value={formatCurrency(rebalanceResult.total_estimated_cost || 0)} icon={<DollarSign className="text-amber-400" />} />
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse font-mono text-sm">
                        <thead className="text-[10px] text-gray-500 uppercase tracking-widest border-b border-white/5">
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
                            <tr key={`${trade.ticker}-${trade.action}`} className="border-b border-white/5">
                              <td className="px-3 py-4 text-white font-bold">{trade.ticker}</td>
                              <td className={cn("px-3 py-4 text-right font-bold", trade.action === "BUY" ? "text-green-400" : "text-red-400")}>{trade.action}</td>
                              <td className="px-3 py-4 text-right text-white">{formatCurrency(trade.amount)}</td>
                              <td className="px-3 py-4 text-right text-gray-300">{Number(trade.shares || 0).toFixed(4).replace(/\.?0+$/, "")}</td>
                              <td className="px-3 py-4 text-right text-gray-300">{formatCurrency(trade.price)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : (
                  <div className="h-full min-h-[320px] flex items-center justify-center text-center text-gray-500">
                    Rebalance analysis will generate drift-aware trade instructions from your live holdings.
                  </div>
                )}
              </div>
            </div>
          </TabsContent>
        </Tabs>
      )}

      <AnimatePresence>
        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShowCreateModal(false)} className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
            <motion.div initial={{ scale: 0.92, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.92, opacity: 0 }} className="relative glass-panel w-full max-w-md p-8 rounded-3xl bg-[#0d0d14] border border-white/10 shadow-2xl">
              <h2 className="text-2xl font-bold text-white mb-6">Create Portfolio</h2>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label className="text-xs uppercase font-bold text-gray-500">Portfolio Name</Label>
                  <Input value={portfolioName} onChange={(event) => setPortfolioName(event.target.value)} placeholder="Main Equity / Growth" className="bg-surface h-12" />
                </div>
                <div className="space-y-2">
                  <Label className="text-xs uppercase font-bold text-gray-500">Description</Label>
                  <Input value={portfolioDescription} onChange={(event) => setPortfolioDescription(event.target.value)} placeholder="Institutional long-only mandate" className="bg-surface h-12" />
                </div>
                <div className="flex gap-3 pt-4">
                  <Button variant="ghost" onClick={() => setShowCreateModal(false)} className="flex-1 h-12 font-bold">Cancel</Button>
                  <Button onClick={handleCreatePortfolio} loading={transactionLoading} className="flex-1 h-12 bg-accent hover:bg-accent/90 text-black font-bold">Create</Button>
                </div>
              </div>
            </motion.div>
          </div>
        )}

        {showTransactionModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShowTransactionModal(false)} className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
            <motion.div initial={{ scale: 0.92, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.92, opacity: 0 }} className="relative glass-panel w-full max-w-lg p-8 rounded-3xl bg-[#0d0d14] border border-white/10 shadow-2xl">
              <h2 className="text-2xl font-bold text-white mb-6">Record Transaction</h2>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label className="text-xs uppercase font-bold text-gray-500">Transaction Type</Label>
                  <select value={transactionType} onChange={(event) => setTransactionType(event.target.value as TransactionType)} className="w-full bg-surface border border-white/5 rounded-xl h-12 px-4 text-sm text-white">
                    {["BUY", "SELL", "DEPOSIT", "WITHDRAWAL", "DIVIDEND", "FEE"].map((type) => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>
                </div>
                {(transactionType === "BUY" || transactionType === "SELL") && (
                  <>
                    <div className="grid grid-cols-3 gap-3">
                      <div className="col-span-1 space-y-2">
                        <Label className="text-xs uppercase font-bold text-gray-500">Ticker</Label>
                        <Input value={symbol} onChange={(event) => setSymbol(event.target.value.toUpperCase())} placeholder="NVDA" className="bg-surface h-12" />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-xs uppercase font-bold text-gray-500">Shares</Label>
                        <Input type="number" value={quantity} onChange={(event) => setQuantity(event.target.value)} className="bg-surface h-12" />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-xs uppercase font-bold text-gray-500">Price</Label>
                        <Input type="number" value={price} onChange={(event) => setPrice(event.target.value)} className="bg-surface h-12" />
                      </div>
                    </div>
                  </>
                )}
                {["DEPOSIT", "WITHDRAWAL", "DIVIDEND", "FEE"].includes(transactionType) && (
                  <div className="space-y-2">
                    <Label className="text-xs uppercase font-bold text-gray-500">Cash Amount</Label>
                    <Input type="number" value={grossAmount} onChange={(event) => setGrossAmount(event.target.value)} className="bg-surface h-12" />
                  </div>
                )}
                <div className="flex gap-3 pt-4">
                  <Button variant="ghost" onClick={() => setShowTransactionModal(false)} className="flex-1 h-12 font-bold">Cancel</Button>
                  <Button onClick={handleRecordTransaction} loading={transactionLoading} className="flex-1 h-12 bg-accent hover:bg-accent/90 text-black font-bold">Save</Button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}
