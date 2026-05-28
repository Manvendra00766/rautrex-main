"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  DollarSign,
  LayoutDashboard,
  ShieldAlert,
  Download,
  ChevronUp,
  ChevronDown
} from "lucide-react"
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { motion, AnimatePresence } from "framer-motion"

import { MetricCard } from "@/components/ui/MetricCard"
import { CardSurface } from "@/components/ui/CardSurface"
import { DataTable, TableHead, TableRow, TableCell } from "@/components/ui/DataTable"
import { SectionHeader } from "@/components/ui/SectionHeader"
import TickerTape from "@/components/ticker-tape"
import { Button } from "@/components/ui/button"
import { usePortfolioOverview } from "@/lib/use-portfolio-overview"
import { cn } from "@/lib/utils"
import { useToast } from "@/components/ui/Toast"
import api from "@/lib/api"
import ChartWrapper from "@/components/ChartWrapper"
import { useSandbox } from "@/lib/sandboxContext"
import { sandboxData } from "@/lib/sandboxData"

const PIE_COLORS = ['#8B6F47', '#EDE8DC', '#8C8278', '#D4CEC4', '#2F6B3D', '#FAF7F2', '#EFE8DF']

function formatPct(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined) return "—";
  return `${value >= 0 ? "+" : ""}${value.toFixed(digits)}%`
}

export default function Dashboard() {
  const router = useRouter()
  const { isSandbox, enterSandbox } = useSandbox()
  const { portfolios, overview: realOverview, loading: realLoading, error: realError } = usePortfolioOverview()
  const [activeCurrency, setActiveCurrency] = useState("USD")

  const formatCurrency = (value: number | null | undefined) => {
    if (value === null || value === undefined) return "—";
    return new Intl.NumberFormat(activeCurrency === "INR" ? "en-IN" : "en-US", {
      style: "currency",
      currency: activeCurrency,
      maximumFractionDigits: 0,
    }).format(value)
  }

  useEffect(() => {
    if (!realLoading && !isSandbox && (!portfolios || portfolios.length === 0)) {
      router.push("/onboarding")
    }
  }, [realLoading, isSandbox, portfolios, router])


  const overview = isSandbox ? (sandboxData as any) : realOverview
  const loading = isSandbox ? false : realLoading
  const error = isSandbox ? null : realError

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

  const [alertsExpanded, setAlertsExpanded] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const { toast } = useToast()

  const handleExportPDF = async () => {
    if (isSandbox) {
      toast({
        type: 'success',
        title: 'Sandbox Export Successful',
        description: 'Simulated PDF generation completed. Real PDF exports require an active workspace.'
      });
      return;
    }
    if (!overview?.portfolio?.id) return;
    
    setIsExporting(true);
    try {
      const portfolioId = overview.portfolio.id;
      const response = await api.get(`/report/export/${portfolioId}`, {
        responseType: 'blob'
      });

      const blob = response.data;
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `rautrex_report_${portfolioId}.pdf`;
      document.body.appendChild(link);
      link.click();
      
      document.body.removeChild(link);
      setTimeout(() => window.URL.revokeObjectURL(url), 5000);
      
      toast({
        type: 'success',
        title: 'Report Downloaded',
        description: 'Your portfolio report has been generated successfully.'
      });
    } catch (err) {
      console.error('PDF Export failed:', err);
      toast({
        type: 'error',
        title: 'Export Failed',
        description: 'Could not generate the PDF report. Please try again.'
      });
    } finally {
      setIsExporting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <Activity className="text-[var(--accent)] animate-spin" size={32} />
      </div>
    )
  }

  if (error) {
    return (
      <CardSurface className="p-8 flex flex-col items-center justify-center gap-4 min-h-[500px]">
        <AlertTriangle className="text-negative" size={40} />
        <p className="text-sm font-mono text-text-secondary">{error}</p>
      </CardSurface>
    )
  }

  if (!overview?.portfolio || !overview.summary) {
    return (
      <div className="space-y-4 max-w-[1800px] mx-auto">
        <TickerTape />
        <CardSurface className="p-8 flex flex-col items-center justify-center text-center space-y-6 min-h-[400px]">
          <div className="w-16 h-16 bg-surface rounded-full flex items-center justify-center">
            <LayoutDashboard className="text-accent" size={32} />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-text-primary">No Active Portfolio</h2>
            <p className="text-text-muted max-w-md mx-auto text-sm leading-relaxed">
              Create or fund a portfolio to unlock live NAV, accounting, and risk analytics across the terminal.
            </p>
          </div>
          <div className="flex flex-col sm:flex-row items-center gap-4">
            <Link href="/dashboard/portfolio">
              <Button className="bg-[#8B6F47] hover:bg-[#8B6F47]/90 text-white font-bold px-8 h-10 tracking-widest uppercase text-xs gap-2 rounded-sm border-none shadow-none">
                <DollarSign size={14} /> OPEN PORTFOLIO LAB
              </Button>
            </Link>
            <Button 
              onClick={enterSandbox}
              variant="outline"
              className="border-[#D4CEC4] hover:bg-[#EDE8DC]/50 text-text-primary font-bold px-8 h-10 tracking-widest uppercase text-xs gap-2 rounded-sm shadow-none bg-surface"
            >
              <Activity size={14} className="text-[#8B6F47]" /> ENTER SANDBOX DEMO
            </Button>
          </div>
        </CardSurface>
      </div>
    )
  }

  const { summary, positions, equity_curve, allocation, warnings } = overview
  const bestPerformer = [...positions].sort((a, b) => b.total_return_pct - a.total_return_pct)[0]
  const worstPerformer = [...positions].sort((a, b) => a.total_return_pct - b.total_return_pct)[0]
  
  const navValues = (equity_curve || []).map((d: any) => d.nav || 0)
  const minNav = navValues.length > 0 ? Math.min(...navValues) : 0
  const maxNav = navValues.length > 0 ? Math.max(...navValues) : 10000
  const yDomain = [
    minNav > 0 ? minNav * 0.95 : 0,
    maxNav > 0 ? maxNav * 1.05 : 10000
  ]
  
  const totalPositionsValue = positions.reduce((sum, pos) => sum + pos.market_value, 0)
  const cashValue = summary.nav - totalPositionsValue
  const allocationData = (allocation?.by_sector || []).map((bucket, i) => ({
    name: bucket.label,
    value: bucket.weight_pct,
    color: PIE_COLORS[i % PIE_COLORS.length]
  }))
  
  if (cashValue > 0) {
    allocationData.push({
      name: 'Cash',
      value: (cashValue / summary.nav) * 100,
      color: 'var(--text-muted)'
    })
  }
  const firstAlertMessage = (overview as any).alerts?.[0]?.message || warnings?.[0]?.message
  const exposureIsEqual = Math.abs((summary.gross_exposure || 0) - (summary.net_exposure || 0)) < 0.01
  const exposureEqualNote = exposureIsEqual ? "Equal because no short positions held" : undefined

  return (
    <div className="space-y-4 max-w-[1800px] mx-auto pb-8">
      {/* Header & Ticker Tape */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
          <div className="flex flex-col md:flex-row md:items-end gap-4">
            <SectionHeader 
              title={overview.portfolio.name} 
              description="Portfolio Command Center" 
              className="mb-0"
            />
            <Button 
              onClick={handleExportPDF}
              disabled={isExporting}
              variant="outline"
              className="bg-surface border-border hover:bg-card text-text-primary text-[10px] tracking-[0.1em] font-bold h-8 px-3 uppercase gap-2 mb-1 rounded-sm shadow-none"
            >
              {isExporting ? (
                <Activity className="animate-spin text-accent" size={14} />
              ) : (
                <Download size={14} className="text-accent" />
              )}
              {isExporting ? "Generating..." : "Export PDF"}
            </Button>
          </div>
          <div className="xl:w-1/2">
            <TickerTape />
          </div>
        </div>
      </div>

      {/* Alerts Bar */}
      {((overview as any).alerts?.length > 0 || warnings.length > 0) && (
        <div className="bg-surface border-l-[3px] border-negative overflow-hidden rounded-sm">
          <button 
            onClick={() => setAlertsExpanded(!alertsExpanded)}
            className="w-full flex items-center justify-between p-2.5 hover:bg-card transition-colors border-b border-border"
          >
            <div className="flex items-center gap-3">
              <AlertTriangle size={14} className="text-negative animate-pulse" />
              <span className="text-xs font-medium text-text-primary">
                {((overview as any).alerts?.length || warnings.length)} Active System {((overview as any).alerts?.length || warnings.length) === 1 ? 'Alert' : 'Alerts'}
              </span>
              {!alertsExpanded && firstAlertMessage && (
                <span className="text-[11px] text-text-secondary truncate max-w-[60vw] text-left">
                  {firstAlertMessage}
                </span>
              )}
            </div>
            {alertsExpanded ? <ChevronUp size={14} className="text-text-muted" /> : <ChevronDown size={14} className="text-text-muted" />}
          </button>
          <AnimatePresence>
            {alertsExpanded && (
              <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden">
                <div className="p-4 flex flex-col gap-3">
                  {(overview as any).alerts && (overview as any).alerts.length > 0 ? (
                    (overview as any).alerts.map((alert: any) => (
                      <div key={alert.id} className="text-[11px] font-mono bg-surface border border-border rounded-sm p-3 flex flex-col md:flex-row md:items-center justify-between gap-3">
                        <div className="flex items-start gap-2.5">
                          <div className={cn(
                            "px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider font-sans",
                            alert.severity === "critical" 
                              ? "bg-negative/10 text-negative border border-negative/20" 
                              : "bg-warning/10 text-warning border border-warning/20"
                          )}>
                            {alert.severity}
                          </div>
                          <div>
                            <p className="font-bold text-text-primary mb-0.5">{alert.title}</p>
                            <p className="text-text-secondary">{alert.message}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3 self-end md:self-center text-text-muted shrink-0 text-[10px]">
                          {alert.affected_asset && (
                            <span className="px-1.5 py-0.5 bg-surface border border-border rounded text-[9px] font-bold text-accent font-sans">
                              {alert.affected_asset}
                            </span>
                          )}
                          <span>
                            {new Date(alert.triggered_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                          </span>
                        </div>
                      </div>
                    ))
                  ) : (
                    warnings.map((warning) => (
                      <div key={warning.code} className="text-[11px] font-mono text-text-secondary flex items-center gap-2 py-0.5">
                        <span className="w-1 h-1 rounded-full bg-negative" />
                        {warning.message}
                      </div>
                    ))
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Row 1: Hero NAV + Core Metrics */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        <div className="xl:col-span-4">
          <MetricCard 
            label="Net Asset Value" 
            value={formatCurrency(summary.nav)} 
            accent={true}
            large={true}
          />
        </div>
        <div className="xl:col-span-8 grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard 
            label="Daily P&L" 
            value={formatCurrency(Math.abs(summary.daily_pnl))} 
            trend={summary.daily_pnl >= 0 ? "up" : "down"}
            change={formatPct(summary.daily_return_pct)} 
          />
          <MetricCard 
            label="MTD Return" 
            value={formatPct(summary.mtd_return_pct)} 
            subtext="Performance this month"
          />
          <MetricCard 
            label="YTD Return" 
            value={formatPct(summary.ytd_return_pct)} 
            subtext="Performance this year"
          />
          <MetricCard 
            label="Cash Balance" 
            value={summary.cash === null || summary.cash === undefined ? "N/A" : formatCurrency(summary.cash)} 
            subtext="Liquid capital"
          />
        </div>
      </div>

      {/* Row 2: Risk & Exposure Analytics */}
      <CardSurface className="p-4 grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Gross Exposure" value={formatCurrency(summary.gross_exposure)} change={formatPct(summary.gross_exposure_pct)} trend={summary.gross_exposure_pct >= 0 ? "up" : "down"} subtext={exposureEqualNote} />
        <MetricCard label="Net Exposure" value={formatCurrency(summary.net_exposure)} change={exposureIsEqual ? undefined : formatPct(summary.net_exposure_pct)} trend={summary.net_exposure_pct >= 0 ? "up" : "down"} subtext={exposureEqualNote} />
        <MetricCard label="Value at Risk (95%)" value={summary.var_95 !== null && summary.var_95 !== undefined ? (Math.abs(summary.var_95 * 100) > 100 ? "Insufficient data for accurate VaR" : formatPct(summary.var_95 * 100)) : "—"} subtext="Max daily potential loss" />
        <MetricCard label="Sharpe Ratio" value={summary.sharpe_ratio !== null && summary.sharpe_ratio !== undefined ? summary.sharpe_ratio.toFixed(2) : "—"} subtext={summary.sharpe_ratio === null || summary.sharpe_ratio === undefined || (summary.sharpe_ratio === 0 && (equity_curve || []).length < 20) ? "Insufficient history (need 20+ days)" : "Risk-adjusted return"} />
      </CardSurface>

      {/* Row 3: Dominant Chart & Sidebars */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        <CardSurface className="xl:col-span-9 p-5 flex flex-col min-h-[460px]">
          <div className="flex justify-between items-start mb-6">
            <SectionHeader 
              title="Portfolio NAV History" 
              description="Historical Equity" 
              className="mb-0"
            />
            <div className="text-right">
              <p className="text-[10px] text-text-muted uppercase tracking-widest font-bold mb-1">Max Drawdown</p>
              <p className="text-lg font-mono font-bold text-negative" title={summary.max_drawdown === 0 || summary.max_drawdown === null ? "Correct for single-day portfolio" : undefined}>
                {summary.max_drawdown !== null && summary.max_drawdown !== undefined ? formatPct(summary.max_drawdown * 100) : "—"}
              </p>
            </div>
          </div>

          <div className="flex-1 w-full" style={{ minHeight: '300px' }}>
            <ChartWrapper height={350}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={equity_curve} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="snapshot_date" stroke="var(--text-muted)" fontSize={11} minTickGap={50} tickMargin={10} axisLine={false} tickLine={false} />
                  <YAxis stroke="var(--text-muted)" fontSize={11} domain={yDomain} tickFormatter={(value) => `${activeCurrency === "INR" ? "₹" : "$"}${value.toLocaleString()}`} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 4, padding: "8px 12px" }}
                    itemStyle={{ color: "var(--accent)", fontWeight: "bold", fontSize: "13px" }}
                    labelStyle={{ color: "var(--text-muted)", fontSize: "10px", marginBottom: "4px", textTransform: "uppercase", letterSpacing: "1px" }}
                    formatter={(value: number) => formatCurrency(value)}
                  />
                  <Area type="monotone" dataKey="nav" stroke="var(--accent)" strokeWidth={2} fill="transparent" />
                </AreaChart>
              </ResponsiveContainer>
            </ChartWrapper>
          </div>
        </CardSurface>

        <div className="xl:col-span-3 flex flex-col gap-4">
          <CardSurface className="p-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-[10px] font-bold uppercase tracking-widest text-text-muted">Performance</h3>
              <Link href="/dashboard/portfolio" className="text-[9px] text-accent font-bold uppercase tracking-widest flex items-center gap-1 hover:text-text-primary transition-colors">
                Book <ArrowRight size={10} />
              </Link>
            </div>
            <div className="space-y-2">
              {[
                { role: "best", position: bestPerformer },
                { role: "worst", position: worstPerformer },
              ]
                .filter((item) => Boolean(item.position))
                .map(({ role, position }) => (
                <div key={`${role}-${position.ticker}`} className="p-3 rounded-sm bg-surface border border-border flex justify-between items-center group hover:bg-card transition-colors">
                  <div>
                    <p className="text-sm font-bold text-text-primary tracking-tight">{position.ticker}</p>
                    <p className="text-[9px] text-text-muted uppercase tracking-widest mt-0.5">{position.sector || position.asset_type}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[13px] font-mono font-bold text-text-primary">{formatCurrency(position.market_value)}</p>
                    <p className={cn("text-[10px] font-mono font-bold mt-0.5", position.total_return_pct >= 0 ? "text-positive" : "text-negative")}>
                      {formatPct(position.total_return_pct)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardSurface>

          <CardSurface className="p-4 flex-1 flex flex-col">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-text-muted mb-4">Asset Allocation</h3>
            <div className="flex-1" style={{ minHeight: '200px' }}>
              <ChartWrapper height={200}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={allocationData} dataKey="value" nameKey="name" innerRadius={60} outerRadius={90} stroke="none" paddingAngle={1}>
                      {allocationData.map((entry, index) => (
                        <Cell key={index} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip 
                      formatter={(value: number) => `${value.toFixed(2)}%`} 
                      contentStyle={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 4 }}
                    />
                    <Legend 
                      formatter={(value, entry: any) => `${value} — ${entry.payload.value.toFixed(1)}%`} 
                      wrapperStyle={{ fontSize: '10px', color: 'var(--text-muted)' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </ChartWrapper>
            </div>
          </CardSurface>
        </div>
      </div>

      {/* Row 4: Live Book */}
      <CardSurface className="p-5">
        <div className="flex justify-between items-end mb-6">
          <SectionHeader 
            title="Active Positions" 
            description="Live Ledger" 
            className="mb-0"
          />
          <div className="text-right">
            <p className="text-[10px] text-text-muted uppercase tracking-widest font-bold mb-0.5">Total Holdings</p>
            <p className="text-lg font-mono font-bold text-accent">{summary.holdings_count}</p>
          </div>
        </div>

        <DataTable>
          <thead>
            <tr>
              <TableHead>Asset</TableHead>
              <TableHead className="text-right">Shares</TableHead>
              <TableHead className="text-right">Cost Basis</TableHead>
              <TableHead className="text-right">Live Price</TableHead>
              <TableHead className="text-right">Market Val</TableHead>
              <TableHead className="text-right">Unrealized</TableHead>
              <TableHead className="text-right">Day P&L</TableHead>
              <TableHead className="text-right">Return</TableHead>
              <TableHead className="text-right">Weight</TableHead>
            </tr>
          </thead>
          <tbody>
            {positions.map((position) => (
              <TableRow key={position.ticker}>
                <TableCell>
                  <div className="flex flex-col">
                    <span className="font-bold text-text-primary text-[13px]">{position.ticker}</span>
                    <span className="text-[9px] text-text-muted uppercase tracking-widest">{position.asset_type}</span>
                  </div>
                </TableCell>
                <TableCell className="text-right text-text-secondary">{position.shares.toFixed(4).replace(/\.?0+$/, "")}</TableCell>
                <TableCell className="text-right text-text-muted">{formatCurrency(position.avg_cost_per_share)}</TableCell>
                <TableCell className="text-right text-text-primary">
                  <div className="flex flex-col items-end">
                    <span>{formatCurrency(position.live_price)}</span>
                    {position.no_live_price && (
                      <span className="text-[8px] text-text-muted font-normal lowercase bg-surface border border-border px-1 rounded select-none">no live price</span>
                    )}
                  </div>
                </TableCell>
                <TableCell className="text-right text-text-primary">{formatCurrency(position.market_value)}</TableCell>
                <TableCell className={cn("text-right font-medium", position.unrealized_pnl >= 0 ? "text-positive" : "text-negative")}>
                  {formatCurrency(position.unrealized_pnl)}
                </TableCell>
                <TableCell className={cn("text-right font-medium", position.daily_pnl >= 0 ? "text-positive" : "text-negative")}>
                  {formatCurrency(position.daily_pnl)}
                </TableCell>
                <TableCell className={cn("text-right font-medium", position.total_return_pct >= 0 ? "text-positive" : "text-negative")}>
                  {formatPct(position.total_return_pct)}
                </TableCell>
                <TableCell className="text-right text-text-primary bg-surface/20 opacity-80">{position.weight_pct.toFixed(2)}%</TableCell>
              </TableRow>
            ))}
          </tbody>
        </DataTable>
      </CardSurface>
    </div>
  )
}
