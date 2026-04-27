"use client"

import { useState } from "react"
import Link from "next/link"
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  DollarSign,
  LayoutDashboard,
  Percent,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
  Wallet,
  ChevronDown,
  ChevronUp
} from "lucide-react"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { motion, AnimatePresence } from "framer-motion"

import MetricCard from "@/components/metric-card"
import TickerTape from "@/components/ticker-tape"
import { Button } from "@/components/ui/button"
import { usePortfolioOverview } from "@/lib/use-portfolio-overview"
import { cn } from "@/lib/utils"


const PIE_COLORS = ["#00d4ff", "#10b981", "#f59e0b", "#7c3aed", "#f43f5e", "#6366f1"]

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

export default function Dashboard() {
  const { overview, loading, error } = usePortfolioOverview()
  const [alertsExpanded, setAlertsExpanded] = useState(false)

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <Activity className="text-accent animate-spin" size={32} />
      </div>
    )
  }

  if (error) {
    return (
      <div className="glass-panel p-12 rounded-3xl flex flex-col items-center justify-center gap-4 min-h-[500px] bg-[#0d0d14]">
        <AlertTriangle className="text-red-500" size={40} />
        <p className="text-sm font-mono text-gray-400">{error}</p>
      </div>
    )
  }

  if (!overview?.portfolio || !overview.summary) {
    return (
      <div className="space-y-8 max-w-[1800px] mx-auto">
        <TickerTape />
        <div className="glass-panel p-16 rounded-3xl flex flex-col items-center justify-center text-center space-y-8 min-h-[600px] bg-[#0d0d14] border border-white/[0.02]">
          <div className="w-24 h-24 bg-accent/5 rounded-full flex items-center justify-center">
            <LayoutDashboard className="text-accent" size={48} />
          </div>
          <div className="space-y-4">
            <h2 className="text-3xl font-black text-white tracking-tight">No Active Portfolio</h2>
            <p className="text-gray-500 max-w-md mx-auto text-sm leading-relaxed">
              Create or fund a portfolio to unlock live NAV, accounting, and risk analytics across the terminal.
            </p>
          </div>
          <Link href="/portfolio">
            <Button className="bg-accent hover:bg-accent/90 text-black font-black px-10 h-14 tracking-widest uppercase text-xs gap-3">
              <DollarSign size={16} /> OPEN PORTFOLIO LAB
            </Button>
          </Link>
        </div>
      </div>
    )
  }

  const { summary, positions, equity_curve, allocation, warnings } = overview
  const bestPerformer = [...positions].sort((a, b) => b.total_return_pct - a.total_return_pct)[0]
  const worstPerformer = [...positions].sort((a, b) => a.total_return_pct - b.total_return_pct)[0]
  const sectorAllocation = allocation.by_sector.slice(0, 6)
  const assetAllocation = allocation.by_asset_type.slice(0, 6)

  return (
    <div className="space-y-8 max-w-[1800px] mx-auto pb-16">
      {/* Header & Ticker Tape */}
      <div className="flex flex-col gap-5">
        <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-6">
          <div>
            <p className="text-[10px] text-gray-500 uppercase tracking-[0.3em] font-bold mb-1">Portfolio Command Center</p>
            <h1 className="text-3xl md:text-4xl font-black text-white tracking-tight">{overview.portfolio.name}</h1>
          </div>
          <div className="xl:w-2/3">
            <TickerTape />
          </div>
        </div>
      </div>

      {/* Alerts Bar (Collapsible, Slimmer) */}
      {warnings.length > 0 && (
        <div className="glass-panel rounded-2xl border border-amber-500/20 bg-amber-500/[0.02] overflow-hidden">
          <button 
            onClick={() => setAlertsExpanded(!alertsExpanded)}
            className="w-full flex items-center justify-between p-4 hover:bg-amber-500/[0.05] transition-colors"
          >
            <div className="flex items-center gap-3">
              <AlertTriangle size={16} className="text-amber-500" />
              <span className="text-xs uppercase tracking-widest font-bold text-amber-500">
                {warnings.length} Active System {warnings.length === 1 ? 'Alert' : 'Alerts'}
              </span>
            </div>
            {alertsExpanded ? <ChevronUp size={16} className="text-amber-500/50" /> : <ChevronDown size={16} className="text-amber-500/50" />}
          </button>
          <AnimatePresence>
            {alertsExpanded && (
              <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden">
                <div className="px-4 pb-4 flex flex-col gap-2">
                  {warnings.map((warning) => (
                    <div key={warning.code} className="text-[11px] font-mono text-amber-200/80 flex items-center gap-3 bg-black/20 p-2.5 rounded-lg border border-amber-500/10">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-500/50" />
                      {warning.message}
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Row 1: Hero NAV + Core Metrics */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        <MetricCard 
          title="Net Asset Value" 
          value={formatCurrency(summary.nav)} 
          className="xl:col-span-4 p-8 bg-gradient-to-br from-[#0d0d14] to-[#12121c] border-white/5"
          valueClassName="text-4xl md:text-5xl lg:text-6xl text-white font-black tracking-tighter mt-4"
        />
        <div className="xl:col-span-8 grid grid-cols-2 md:grid-cols-4 gap-6">
          <MetricCard 
            title="Daily P&L" 
            value={formatCurrency(Math.abs(summary.daily_pnl))} 
            trend={formatPct(summary.daily_return_pct)} 
            trendColor={summary.daily_pnl >= 0 ? "text-green-500" : "text-red-500"}
            valueClassName={summary.daily_pnl >= 0 ? "text-green-400" : "text-red-400"}
          />
          <MetricCard 
            title="MTD Return" 
            value={formatPct(summary.mtd_return_pct)} 
            valueClassName="text-cyan-400" 
          />
          <MetricCard 
            title="YTD Return" 
            value={formatPct(summary.ytd_return_pct)} 
            valueClassName="text-purple-400" 
          />
          <MetricCard 
            title="Cash Balance" 
            value={formatCurrency(summary.cash)} 
            valueClassName="text-amber-400" 
          />
        </div>
      </div>

      {/* Row 2: Risk & Exposure Analytics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        <MetricCard 
          title="Gross Exposure" 
          value={formatCurrency(summary.gross_exposure)} 
          trend={formatPct(summary.gross_exposure_pct)} 
          icon={<ShieldAlert size={24} className="text-blue-400" />} 
        />
        <MetricCard 
          title="Net Exposure" 
          value={formatCurrency(summary.net_exposure)} 
          trend={formatPct(summary.net_exposure_pct)} 
          icon={<ShieldAlert size={24} className="text-indigo-400" />} 
        />
        <MetricCard 
          title="Value at Risk (95%)" 
          value={formatPct(summary.var_95 * 100)} 
          icon={<AlertTriangle size={24} className="text-orange-400" />} 
          valueClassName="text-orange-400"
        />
        <MetricCard 
          title="Sharpe Ratio" 
          value={(summary.sharpe_ratio || 0).toFixed(2)} 
          icon={<Activity size={24} className="text-white" />} 
        />
      </div>

      {/* Row 3: Dominant Chart & Sidebars */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
        
        {/* Centerpiece Chart */}
        <div className="xl:col-span-9 glass-panel p-8 rounded-3xl min-h-[560px] bg-[#0d0d14] flex flex-col border border-white/[0.02]">
          <div className="flex justify-between items-start mb-8">
            <div>
              <p className="text-[10px] text-gray-500 uppercase tracking-[0.3em] font-bold mb-2">Historical Equity</p>
              <h3 className="text-2xl font-black text-white tracking-tight">Portfolio NAV History</h3>
            </div>
            <div className="text-right">
              <p className="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1">Max Drawdown</p>
              <p className="text-xl font-mono font-bold text-red-400">{formatPct(summary.max_drawdown * 100)}</p>
            </div>
          </div>

          <div className="flex-1 w-full min-h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={equity_curve} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="navGradientHero" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#00d4ff" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#00d4ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                <XAxis dataKey="snapshot_date" stroke="rgba(255,255,255,0.2)" fontSize={11} minTickGap={50} tickMargin={10} axisLine={false} tickLine={false} />
                <YAxis stroke="rgba(255,255,255,0.2)" fontSize={11} tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#11121a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, padding: "12px 16px" }}
                  itemStyle={{ color: "#00d4ff", fontWeight: "bold", fontSize: "14px" }}
                  labelStyle={{ color: "#888", fontSize: "11px", marginBottom: "4px", textTransform: "uppercase", letterSpacing: "1px" }}
                  formatter={(value: number) => formatCurrency(value)}
                />
                <Area type="monotone" dataKey="nav" stroke="#00d4ff" strokeWidth={3} fill="url(#navGradientHero)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right Sidebar: Leaders/Laggards & Allocations */}
        <div className="xl:col-span-3 flex flex-col gap-8">
          <div className="glass-panel p-6 rounded-3xl bg-[#0d0d14] border border-white/[0.02]">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500">Performance</h3>
              <Link href="/portfolio" className="text-[10px] text-accent font-bold uppercase tracking-widest flex items-center gap-1 hover:text-white transition-colors">
                Book <ArrowRight size={12} />
              </Link>
            </div>
            <div className="space-y-3">
              {[bestPerformer, worstPerformer].filter(Boolean).map((position, i) => (
                <div key={position.ticker} className="p-4 rounded-2xl bg-surface border border-white/[0.03] flex justify-between items-center group hover:bg-[#151520] transition-colors">
                  <div>
                    <p className="text-sm font-black text-white tracking-tight">{position.ticker}</p>
                    <p className="text-[9px] text-gray-500 uppercase tracking-widest mt-1">{position.sector || position.asset_type}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-mono font-bold text-white">{formatCurrency(position.market_value)}</p>
                    <p className={cn("text-[11px] font-mono font-bold mt-1", position.total_return_pct >= 0 ? "text-green-400" : "text-red-400")}>
                      {formatPct(position.total_return_pct)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-panel p-6 rounded-3xl bg-[#0d0d14] border border-white/[0.02] flex-1 flex flex-col">
            <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-6">Asset Allocation</h3>
            <div className="flex-1 min-h-[220px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={assetAllocation} dataKey="weight_pct" nameKey="label" innerRadius="65%" outerRadius="90%" stroke="none" paddingAngle={2}>
                    {assetAllocation.map((_, index) => (
                      <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    formatter={(value: number) => `${value.toFixed(2)}%`} 
                    contentStyle={{ backgroundColor: "#11121a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12 }}
                    itemStyle={{ fontWeight: "bold" }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Row 4: Live Book */}
      <div className="glass-panel p-8 rounded-3xl bg-[#0d0d14] border border-white/[0.02]">
        <div className="flex justify-between items-end mb-8">
          <div>
            <p className="text-[10px] text-gray-500 uppercase tracking-[0.3em] font-bold mb-2">Live Ledger</p>
            <h3 className="text-2xl font-black text-white tracking-tight">Active Positions</h3>
          </div>
          <div className="text-right">
            <p className="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1">Total Holdings</p>
            <p className="text-2xl font-mono font-black text-accent">{summary.holdings_count}</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse font-mono text-sm">
            <thead className="text-[10px] text-gray-500 uppercase tracking-[0.2em] border-b border-white/5">
              <tr>
                <th className="px-4 py-4">Asset</th>
                <th className="px-4 py-4 text-right">Shares</th>
                <th className="px-4 py-4 text-right">Cost Basis</th>
                <th className="px-4 py-4 text-right">Live Price</th>
                <th className="px-4 py-4 text-right">Market Val</th>
                <th className="px-4 py-4 text-right">Unrealized</th>
                <th className="px-4 py-4 text-right">Day P&L</th>
                <th className="px-4 py-4 text-right">Return</th>
                <th className="px-4 py-4 text-right">Weight</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((position) => (
                <tr key={position.ticker} className="border-b border-white/[0.03] hover:bg-[#11111a] transition-colors group">
                  <td className="px-4 py-5">
                    <div className="flex flex-col gap-1">
                      <span className="font-black text-white text-base tracking-tight">{position.ticker}</span>
                      <span className="text-[9px] text-gray-500 uppercase tracking-widest">{position.asset_type}</span>
                    </div>
                  </td>
                  <td className="px-4 py-5 text-right text-gray-300 font-bold">{position.shares.toFixed(4).replace(/\.?0+$/, "")}</td>
                  <td className="px-4 py-5 text-right text-gray-400">{formatCurrency(position.avg_cost_per_share)}</td>
                  <td className="px-4 py-5 text-right text-white font-bold">{formatCurrency(position.live_price)}</td>
                  <td className="px-4 py-5 text-right text-white font-bold">{formatCurrency(position.market_value)}</td>
                  <td className={cn("px-4 py-5 text-right font-bold", position.unrealized_pnl >= 0 ? "text-green-400" : "text-red-400")}>
                    {formatCurrency(position.unrealized_pnl)}
                  </td>
                  <td className={cn("px-4 py-5 text-right font-bold", position.daily_pnl >= 0 ? "text-green-400" : "text-red-400")}>
                    {formatCurrency(position.daily_pnl)}
                  </td>
                  <td className={cn("px-4 py-5 text-right font-bold", position.total_return_pct >= 0 ? "text-green-400" : "text-red-400")}>
                    {formatPct(position.total_return_pct)}
                  </td>
                  <td className="px-4 py-5 text-right text-accent font-bold bg-accent/[0.02]">{position.weight_pct.toFixed(2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
