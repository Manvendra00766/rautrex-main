"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Briefcase,
  DollarSign,
  Link2,
  Percent,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Award,
  ShieldAlert,
  Loader2,
  UploadCloud,
  Lock
} from "lucide-react"
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from "recharts"
import { motion, AnimatePresence } from "framer-motion"

import { MetricCard } from "@/components/ui/MetricCard"
import { CardSurface } from "@/components/ui/CardSurface"
import { DataTable, TableHead, TableRow, TableCell } from "@/components/ui/DataTable"
import { SectionHeader } from "@/components/ui/SectionHeader"
import { Button } from "@/components/ui/button"
import api, { apiFetch } from "@/lib/api"
import { cn } from "@/lib/utils"
import { useToast } from "@/components/ui/Toast"

const PIE_COLORS = ["#14B8A6", "#3B82F6", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#10B981"]

function formatCurrency(value: number | null | undefined) {
  if (value === null || value === undefined) return "—"
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value)
}

function formatPct(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined) return "—"
  return `${value >= 0 ? "+" : ""}${value.toFixed(digits)}%`
}

export default function ImportedPortfolioPage() {
  const router = useRouter()
  const { toast } = useToast()
  
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [portfolioData, setPortfolioData] = useState<any>(null)
  const [isSandbox, setIsSandbox] = useState(false)
  
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [casPassword, setCasPassword] = useState("")
  const [casCashBalance, setCasCashBalance] = useState("0")
  const [uploadingCas, setUploadingCas] = useState(false)
  const [casError, setCasError] = useState<string | null>(null)

  const handleCasUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedFile) return

    setUploadingCas(true)
    setCasError(null)

    try {
      const formData = new FormData()
      formData.append("file", selectedFile)
      if (casPassword) {
        formData.append("password", casPassword)
      }
      formData.append("cash_balance", parseFloat(casCashBalance || "0").toString())

      // Call Axios API upload directly (Axios handles multipart FormDatas automatically)
      const res = await api.post("/onboarding/upload-cas", formData, {
        headers: {
          "Content-Type": "multipart/form-data"
        }
      })
      
      toast({
        type: "success",
        title: "Statement Uploaded!",
        description: `Successfully parsed ${res.data.holdings_count} holdings from your CAS PDF.`
      })

      // Reload portfolio data
      await loadPortfolio()
    } catch (err: any) {
      console.error(err)
      const message = err.response?.data?.detail || err.message || "Failed to process CAS statement."
      setCasError(message)
      toast({
        type: "error",
        title: "Parsing Failed",
        description: message
      })
    } finally {
      setUploadingCas(false)
    }
  }

  // Load imported portfolio from backend
  const loadPortfolio = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiFetch("/onboarding/imported-portfolio")
      setPortfolioData(data)
    } catch (err: any) {
      console.warn("Failed to fetch imported portfolio:", err.message)
      // If 404, we show the link broker prompt
      if (err.message && err.message.includes("404") || err.message.includes("No imported portfolio found")) {
        setPortfolioData(null)
      } else {
        setError(err.message || "Failed to load imported portfolio telemetry.")
      }
    } finally {
      setLoading(false)
    }
  }

  const handleExecuteRebalance = (rec: any) => {
    if (rec.category === "Asset Allocation" || rec.category === "Portfolio Overlap" || rec.category === "Diversification") {
      toast({
        type: "success",
        title: "Redirecting to Zerodha...",
        description: "Preparing your basket order for pre-filled execution."
      })
      
      setTimeout(() => {
        const apiKey = process.env.NEXT_PUBLIC_KITE_API_KEY || "rautrex-kite-key"
        const form = document.createElement("form")
        form.method = "POST"
        form.action = "https://kite.zerodha.com/connect/basket"
        
        const keyInput = document.createElement("input")
        keyInput.type = "hidden"
        keyInput.name = "api_key"
        keyInput.value = apiKey
        
        const basketData = [
          { variety: "regular", tradingsymbol: "TCS", transaction_type: "SELL", order_type: "MARKET", quantity: 3 },
          { variety: "regular", tradingsymbol: "GOLDBEES", transaction_type: "BUY", order_type: "MARKET", quantity: 200 }
        ]
        
        const dataInput = document.createElement("input")
        dataInput.type = "hidden"
        dataInput.name = "data"
        dataInput.value = JSON.stringify(basketData)
        
        form.appendChild(keyInput)
        form.appendChild(dataInput)
        document.body.appendChild(form)
        form.submit()
        document.body.removeChild(form)
        
        toast({
          type: "success",
          title: "Basket Loaded!",
          description: "Trades pre-filled on Zerodha Kite. Click 'Swipe to Execute'."
        })
      }, 1500)
    } else {
      toast({
        type: "success",
        title: "Action Logged",
        description: `Recommendation for '${rec.title}' has been successfully logged. Reviewing telemetry update.`
      })
    }
  }

  useEffect(() => {
    loadPortfolio()
  }, [])

  // Enter Sandbox Demo mode with Zerodha simulated portfolio
  const enterSandboxDemo = () => {
    setIsSandbox(true)
    // Setup rich simulated portfolio data
    const mockHoldings = [
      { ticker: "TCS.NS", name: "Tata Consultancy Services Ltd", asset_type: "equity", sector: "Technology", market_cap_type: "large", shares: 15, avg_cost: 3200.0, current_price: 3450.0, total_invested: 48000.0, current_value: 51750.0, pnl: 3750.0, pnl_pct: 7.81, expense_ratio: 0.0, category: "" },
      { ticker: "RELIANCE.NS", name: "Reliance Industries Ltd", asset_type: "equity", sector: "Energy/Conglomerate", market_cap_type: "large", shares: 25, avg_cost: 2100.0, current_price: 2400.0, total_invested: 52500.0, current_value: 60000.0, pnl: 7500.0, pnl_pct: 14.28, expense_ratio: 0.0, category: "" },
      { ticker: "HDFCBANK.NS", name: "HDFC Bank Ltd", asset_type: "equity", sector: "Banking/Financial Services", market_cap_type: "large", shares: 35, avg_cost: 1500.0, current_price: 1650.0, total_invested: 52500.0, current_value: 57750.0, pnl: 5250.0, pnl_pct: 10.0, expense_ratio: 0.0, category: "" },
      { ticker: "INFY.NS", name: "Infosys Ltd", asset_type: "equity", sector: "Technology", market_cap_type: "large", shares: 30, avg_cost: 1400.0, current_price: 1520.0, total_invested: 42000.0, current_value: 45600.0, pnl: 3600.0, pnl_pct: 8.57, expense_ratio: 0.0, category: "" },
      { ticker: "ICICIBANK.NS", name: "ICICI Bank Ltd", asset_type: "equity", sector: "Banking/Financial Services", market_cap_type: "large", shares: 40, avg_cost: 850.0, current_price: 930.0, total_invested: 34000.0, current_value: 37200.0, pnl: 3200.0, pnl_pct: 9.41, expense_ratio: 0.0, category: "" },
      { ticker: "TATAMOTORS.NS", name: "Tata Motors Ltd", asset_type: "equity", sector: "Automotive", market_cap_type: "large", shares: 60, avg_cost: 550.0, current_price: 615.0, total_invested: 33000.0, current_value: 36900.0, pnl: 3900.0, pnl_pct: 11.81, expense_ratio: 0.0, category: "" },
      { ticker: "BHARTIARTL.NS", name: "Bharti Airtel Ltd", asset_type: "equity", sector: "Telecom", market_cap_type: "large", shares: 40, avg_cost: 780.0, current_price: 850.0, total_invested: 31200.0, current_value: 34000.0, pnl: 2800.0, pnl_pct: 8.97, expense_ratio: 0.0, category: "" },
      { ticker: "LTIM.NS", name: "LTIMindtree Ltd", asset_type: "equity", sector: "Technology", market_cap_type: "large", shares: 8, avg_cost: 4800.0, current_price: 5100.0, total_invested: 38400.0, current_value: 40800.0, pnl: 2400.0, pnl_pct: 6.25, expense_ratio: 0.0, category: "" },
      { ticker: "MIRAE_LARGECAP", name: "Mirae Asset Large Cap Fund", asset_type: "mutual_fund", sector: "Diversified Mutual Fund", market_cap_type: "large", shares: 500.0, avg_cost: 75.0, current_price: 85.0, total_invested: 37500.0, current_value: 42500.0, pnl: 5000.0, pnl_pct: 13.33, expense_ratio: 1.1, category: "equity" },
      { ticker: "AXIS_SMALLCAP", name: "Axis Small Cap Fund", asset_type: "mutual_fund", sector: "Diversified Mutual Fund", market_cap_type: "small", shares: 464.0, avg_cost: 50.0, current_price: 58.0, total_invested: 23200.0, current_value: 26912.0, pnl: 3712.0, pnl_pct: 16.0, expense_ratio: 1.4, category: "equity" },
      { ticker: "SBI_BLUECHIP", name: "SBI Blue Chip Fund", asset_type: "mutual_fund", sector: "Diversified Mutual Fund", market_cap_type: "large", shares: 300.0, avg_cost: 60.0, current_price: 68.0, total_invested: 18000.0, current_value: 20400.0, pnl: 2400.0, pnl_pct: 13.33, expense_ratio: 1.2, category: "equity" },
      { ticker: "PP_FLEXICAP", name: "Parag Parikh Flexi Cap Fund", asset_type: "mutual_fund", sector: "Diversified Mutual Fund", market_cap_type: "large", shares: 200.0, avg_cost: 45.0, current_price: 54.0, total_invested: 9000.0, current_value: 10800.0, pnl: 1800.0, pnl_pct: 20.0, expense_ratio: 0.9, category: "equity" },
      { ticker: "GOLDBEES.NS", name: "Nippon India Gold BeES", "asset_type": "etf", "sector": "Commodity", "market_cap_type": "large", "shares": 250, "avg_cost": 45.0, "current_price": 50.0, "total_invested": 11250.0, "current_value": 12500.0, "pnl": 1250.0, "pnl_pct": 11.11, "expense_ratio": 0.5, "category": "commodity" },
      { ticker: "NIFTYBEES.NS", name: "Nifty 50 ETF", "asset_type": "etf", "sector": "Diversified", "market_cap_type": "large", "shares": 60, "avg_cost": 190.0, "current_price": 215.0, "total_invested": 11400.0, "current_value": 12900.0, "pnl": 1500.0, "pnl_pct": 13.15, "expense_ratio": 0.2, "category": "equity" }
    ]
    
    const mockAnalysis = {
      total_invested: 439000.0,
      current_value: 483012.0,
      overall_pnl: 44012.0,
      overall_pnl_pct: 10.03,
      diversification_score: 93,
      risk_assessment: "Aggressive",
      annual_fee_leakage: 1004.77,
      weighted_expense_ratio: 1.05,
      sector_concentration: {
        "Technology": { value: 138150.0, pct: 28.6 },
        "Banking/Financial Services": { value: 94950.0, pct: 19.7 },
        "Energy/Conglomerate": { value: 60000.0, pct: 12.4 },
        "Automotive": { value: 36900.0, pct: 7.6 },
        "Telecom": { value: 34000.0, pct: 7.0 },
        "Diversified Mutual Fund": { value: 100612.0, pct: 20.8 },
        "Commodity": { value: 12500.0, pct: 2.6 },
        "Diversified": { value: 12900.0, pct: 2.7 }
      },
      sector_warnings: [],
      market_cap_distribution: {
        "large": { value: 443600.0, pct: 91.8 },
        "mid": { value: 0.0, pct: 0.0 },
        "small": { value: 26912.0, pct: 5.6 },
        "micro": { value: 0.0, pct: 0.0 },
        "unclassified": { value: 12500.0, pct: 2.6 }
      },
      asset_type_distribution: {
        "equity": { value: 358750.0, pct: 74.3 },
        "mutual_fund": { value: 100612.0, pct: 20.8 },
        "etf": { value: 25400.0, pct: 5.3 },
        "gold": { value: 0.0, pct: 0.0 },
        "debt": { value: 0.0, pct: 0.0 },
        "other": { value: 0.0, pct: 0.0 }
      },
      top_performers: [
        { ticker: "PP_FLEXICAP", name: "Parag Parikh Flexi Cap Fund", pnl_pct: 20.0, pnl: 1800.0 },
        { ticker: "AXIS_SMALLCAP", name: "Axis Small Cap Fund", pnl_pct: 16.0, pnl: 3712.0 },
        { ticker: "RELIANCE.NS", name: "Reliance Industries Ltd", pnl_pct: 14.28, pnl: 7500.0 }
      ],
      underperformers: [
        { ticker: "LTIM.NS", name: "LTIMindtree Ltd", pnl_pct: 6.25, pnl: 2400.0 },
        { ticker: "TCS.NS", name: "Tata Consultancy Services Ltd", pnl_pct: 7.81, pnl: 3750.0 },
        { ticker: "INFY.NS", name: "Infosys Ltd", pnl_pct: 8.57, pnl: 3600.0 }
      ],
      overlap_analysis: [
        { fund_a: "Mirae Asset Large Cap Fund", fund_b: "SBI Blue Chip Fund", overlap_pct: 65.0, common_holdings: ["HDFC Bank", "Reliance Industries", "ICICI Bank"], risk_level: "High" }
      ],
      gap_analysis: {
        target_risk_profile: "Aggressive",
        actual: { equity: 95.1, debt: 0.0, gold: 4.9 },
        ideal: { equity: 75.0, debt: 15.0, gold: 10.0 },
        gaps: { equity: 20.1, debt: -15.0, gold: -5.1 }
      },
      recommendations: [
        {
          category: "Fees",
          title: "High Expense Ratio Drag",
          description: "Your mutual funds have a high weighted expense ratio of 1.05%. Switching to 'Direct' plans instead of 'Regular' plans can save you around ₹4,300 annually.",
          action: "Switch to Direct Plans"
        },
        {
          category: "Portfolio Overlap",
          title: "Mutual Fund Overlap Detected",
          description: "'Mirae Asset Large Cap Fund' and 'SBI Blue Chip Fund' have a 65% overlap. They both hold similar underlying stocks like HDFC Bank, Reliance, and ICICI Bank. Keeping both adds no diversification benefit.",
          action: "Consolidate Mutual Funds"
        },
        {
          category: "Asset Allocation",
          title: "Equity Over-allocated",
          description: "Your portfolio is over-allocated in Equity by 20.1% compared to your ideal 75% target based on an aggressive risk tolerance. Consider rebalancing into short-term debt.",
          action: "Rebalance Portfolio"
        }
      ]
    }
    
    setPortfolioData({
      broker: "zerodha (sandbox demo)",
      holdings: mockHoldings,
      analysis: mockAnalysis,
      synced_at: new Date().toISOString()
    })
    
    toast({
      type: "success",
      title: "Sandbox Active",
      description: "Displaying simulated Zerodha portfolio data with full footprint analysis."
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <Loader2 className="text-[var(--accent)] animate-spin" size={32} />
      </div>
    )
  }

  if (error) {
    return (
      <CardSurface className="p-8 flex flex-col items-center justify-center gap-4 min-h-[500px]">
        <AlertTriangle className="text-negative animate-bounce" size={40} />
        <h3 className="text-lg font-bold text-[var(--text-primary)]">Sync Load Failed</h3>
        <p className="text-sm font-mono text-text-secondary text-center max-w-md">{error}</p>
        <Button onClick={loadPortfolio} className="bg-[#8B6F47] hover:bg-[#8B6F47]/90 text-[var(--text-primary)] px-6">
          RETRY LOAD
        </Button>
      </CardSurface>
    )
  }

  if (!portfolioData) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-[1400px] mx-auto pb-8">
        
        {/* Left Column: Direct Sync & Sandbox */}
        <CardSurface className="p-10 flex flex-col items-center justify-center text-center space-y-6 min-h-[480px]">
          <div className="w-16 h-16 bg-teal-500/10 rounded-full flex items-center justify-center text-teal-600 shadow-inner">
            <Link2 size={32} className="animate-pulse" />
          </div>
          <div className="space-y-2 max-w-md">
            <span className="text-xs font-bold uppercase tracking-[0.2em] text-teal-600 bg-teal-500/10 px-3 py-1 rounded-full">
              Unified Live Tracking
            </span>
            <h2 className="text-2xl font-extrabold text-[var(--text-primary)] tracking-tight pt-2">
              Connect Broker Demat
            </h2>
            <p className="text-text-muted text-xs leading-relaxed">
              Connect your Zerodha, Groww, or Upstox account to scan your entire external portfolio, run deep quantitative diagnostics, track overlapping risks, and unlock direct recommendations.
            </p>
          </div>
          
          <div className="flex flex-col sm:flex-row items-center gap-4 pt-3">
            <Link href="/onboarding">
              <Button className="bg-[#8B6F47] hover:bg-[#8B6F47]/90 text-[var(--text-primary)] font-bold px-8 h-11 tracking-wider uppercase text-xs gap-2 rounded-sm border-none shadow-md">
                <Link2 size={14} /> LINK BROKER DEMAT
              </Button>
            </Link>
            <Button 
              onClick={enterSandboxDemo}
              variant="outline"
              className="border-[#D4CEC4] hover:bg-[#EDE8DC]/50 text-text-primary font-bold px-8 h-11 tracking-wider uppercase text-xs gap-2 rounded-sm shadow-sm bg-card"
            >
              <Activity size={14} className="text-[#8B6F47]" /> PREVIEW SANDBOX DEMO
            </Button>
          </div>
        </CardSurface>

        {/* Right Column: CAS Statement PDF Uploader */}
        <CardSurface className="p-10 flex flex-col justify-between space-y-6 min-h-[480px]">
          <div className="space-y-2 text-center">
            <span className="text-xs font-bold uppercase tracking-[0.2em] text-amber-600 bg-amber-500/10 px-3 py-1 rounded-full">
              Offline Statement Sync
            </span>
            <h2 className="text-2xl font-extrabold text-[var(--text-primary)] tracking-tight pt-2">
              Upload CAS PDF
            </h2>
            <p className="text-text-muted text-xs leading-relaxed max-w-md mx-auto">
              Don't want to connect your live broker API? Drag & drop your CDSL or NSDL Consolidated Account Statement (CAS) PDF. We decrypt and parse it securely in-memory.
            </p>
          </div>

          <form onSubmit={handleCasUpload} className="space-y-4">
            {/* File Drag and Drop / Input Area */}
            <div className="relative group border border-dashed border-[var(--border)] hover:border-teal-500/50 rounded-lg p-6 text-center transition-all bg-card/50">
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    setSelectedFile(e.target.files[0])
                    setCasError(null)
                  }
                }}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              
              <div className="flex flex-col items-center justify-center space-y-2">
                <div className="w-12 h-12 bg-amber-500/10 rounded-full flex items-center justify-center text-amber-600 shadow-inner group-hover:scale-105 transition-transform">
                  <UploadCloud size={24} />
                </div>
                
                {selectedFile ? (
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-[var(--text-primary)]">
                      {selectedFile.name}
                    </p>
                    <p className="text-xs text-[var(--text-muted)]">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                ) : (
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-[var(--text-primary)]">
                      Click or drag CAS PDF here
                    </p>
                    <p className="text-xs text-[var(--text-muted)]">
                      Supports password-protected CDSL/NSDL files
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Optional Password Input */}
            <div className="space-y-1.5">
              <label htmlFor="cas-password" className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] flex items-center gap-1.5">
                <Lock size={10} /> PDF Password (if protected)
              </label>
              <input
                id="cas-password"
                type="password"
                placeholder="E.g., PAN in UPPERCASE or email"
                value={casPassword}
                onChange={(e) => setCasPassword(e.target.value)}
                className="w-full bg-card border border-[var(--border)] rounded px-3 py-2 text-xs focus:outline-none focus:border-teal-500 text-[var(--text-primary)]"
              />
              <p className="text-xs text-[var(--text-muted)] leading-normal">
                Note: Your password is used purely in-memory on the backend to decrypt the document. We never store or log it.
              </p>
            </div>

            {/* Optional Cash Balance Input */}
            <div className="space-y-1.5">
              <label htmlFor="cas-cash-balance" className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] flex items-center gap-1.5">
                <DollarSign size={10} /> Spare Cash in Your Broker (Optional)
              </label>
              <input
                id="cas-cash-balance"
                type="number"
                placeholder="E.g., 5000"
                value={casCashBalance}
                onChange={(e) => setCasCashBalance(e.target.value)}
                className="w-full bg-card border border-[var(--border)] rounded px-3 py-2 text-xs focus:outline-none focus:border-teal-500 text-[var(--text-primary)]"
              />
              <p className="text-xs text-[var(--text-muted)] leading-normal">
                If you have uninvested spare cash sitting in your broker account, enter it here to compute your true cash weight accurately. Defaults to ₹0.
              </p>
            </div>

            {casError && (
              <p className="text-xs text-red-500 font-medium">
                {casError}
              </p>
            )}

            {/* Submit Button */}
            <Button
              type="submit"
              disabled={!selectedFile || uploadingCas}
              className={cn(
                "w-full text-[var(--text-primary)] font-bold h-11 tracking-wider uppercase text-xs rounded-sm shadow-md transition-all border-none",
                selectedFile && !uploadingCas 
                  ? "bg-teal-600 hover:bg-teal-500" 
                  : "bg-teal-800/40 text-[var(--text-primary)]/50 cursor-not-allowed"
              )}
            >
              {uploadingCas ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="animate-spin" size={14} /> PARSING STATEMENT...
                </span>
              ) : (
                "UPLOAD AND SCAN HOLDINGS"
              )}
            </Button>
          </form>
        </CardSurface>

      </div>
    )
  }

  const { broker, holdings, analysis, synced_at } = portfolioData
  
  // Format data for Recharts Pie (Asset Allocation)
  const assetAllocationData = Object.entries(analysis.asset_type_distribution)
    .filter(([_, data]: any) => data.value > 0)
    .map(([key, data]: any, idx) => ({
      name: key.toUpperCase(),
      value: data.value,
      pct: data.pct,
      color: PIE_COLORS[idx % PIE_COLORS.length]
    }))

  // Format data for Recharts Bar (Sector concentration)
  const sectorConcentrationData = Object.entries(analysis.sector_concentration)
    .map(([key, data]: any) => ({
      name: key,
      value: data.value,
      pct: data.pct
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 5) // Show top 5 sectors

  const totalInvested = analysis.total_invested || 0
  const currentValue = analysis.current_value || 0
  const overallPnL = analysis.overall_pnl || 0
  const overallPnLPct = analysis.overall_pnl_pct || 0
  const diversificationScore = analysis.diversification_score || 50
  const riskAssessment = analysis.risk_assessment || "Moderate"

  return (
    <div className="space-y-6 max-w-[1800px] mx-auto pb-12">
      
      {/* Header bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--border)]/40 pb-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-[0.2em] text-teal-600 bg-teal-500/10 px-3 py-1 rounded-full">
            Linked Broker Dashboard
          </span>
          <h1 className="text-3xl font-extrabold text-[var(--text-primary)] tracking-tight mt-2 flex items-center gap-2">
            Unified Portfolio Analytics <span className="text-sm font-normal text-[var(--text-muted)]">({broker.toUpperCase()})</span>
          </h1>
          <p className="text-xs text-[var(--text-muted)] mt-1">
            Demat footprint synced at: {new Date(synced_at).toLocaleString("en-IN")} {isSandbox && <strong className="text-teal-600 uppercase tracking-widest ml-1">(Sandbox Mode)</strong>}
          </p>
        </div>
        
        {isSandbox && (
          <Button 
            onClick={() => {
              setIsSandbox(false)
              setPortfolioData(null)
              loadPortfolio()
            }} 
            variant="outline"
            className="border-red-200 hover:bg-red-50 text-red-600 font-bold px-4 h-9 tracking-wider uppercase text-xs gap-2 rounded-sm"
          >
            Exit Sandbox Preview
          </Button>
        )}
      </div>

      {/* Warnings Banner if any */}
      {analysis.sector_warnings && analysis.sector_warnings.length > 0 && (
        <div className="bg-red-500/10 border-l-[3px] border-red-500 rounded-sm p-4 text-xs space-y-2">
          <h4 className="font-bold text-red-950 flex items-center gap-2">
            <ShieldAlert size={14} /> Concentration Exposure Warnings
          </h4>
          <ul className="list-disc pl-5 font-mono text-red-900 space-y-1">
            {analysis.sector_warnings.map((warn: string, i: number) => (
              <li key={i}>{warn}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Row 1: Core Telemetry Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard 
          label="Current Telemetry Value" 
          value={formatCurrency(currentValue)} 
          accent={true}
          large={true}
        />
        <MetricCard 
          label="Total Net Invested" 
          value={formatCurrency(totalInvested)} 
          subtext="Net capital contributed"
        />
        <MetricCard 
          label="Total Unconsolidated P&L" 
          value={formatCurrency(overallPnL)} 
          trend={overallPnL >= 0 ? "up" : "down"}
          change={formatPct(overallPnLPct)} 
        />
        <MetricCard 
          label="Annualised Demat XIRR" 
          value={`${analysis.xirr || 0}%`} 
          subtext={`Simulated over ${holdings.length} holdings`}
        />
      </div>

      {/* Row 2: Secondary Risk Metrics */}
      <CardSurface className="p-4 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="flex items-center gap-4 p-2 bg-[var(--bg-primary)]/20 border border-[var(--border)]/20 rounded-xl">
          <div className="w-12 h-12 bg-teal-500/10 text-teal-600 rounded-full flex items-center justify-center shrink-0">
            <Award size={20} />
          </div>
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">Diversification Score</span>
            <p className="text-xl font-extrabold text-[var(--text-primary)] mt-0.5">{diversificationScore} / 100</p>
            <span className="text-xs text-[var(--text-muted)]">{diversificationScore >= 80 ? "Optimal portfolio index" : "High concentration risks"}</span>
          </div>
        </div>
        
        <div className="flex items-center gap-4 p-2 bg-[var(--bg-primary)]/20 border border-[var(--border)]/20 rounded-xl">
          <div className="w-12 h-12 bg-blue-500/10 text-blue-600 rounded-full flex items-center justify-center shrink-0">
            <ShieldAlert size={20} />
          </div>
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">Volatility Risk Level</span>
            <p className="text-xl font-extrabold text-[var(--text-primary)] mt-0.5">{riskAssessment}</p>
            <span className="text-xs text-[var(--text-muted)]">Based on asset weights</span>
          </div>
        </div>

        <div className="flex items-center gap-4 p-2 bg-[var(--bg-primary)]/20 border border-[var(--border)]/20 rounded-xl">
          <div className="w-12 h-12 bg-red-500/10 text-red-500 rounded-full flex items-center justify-center shrink-0">
            <Percent size={20} />
          </div>
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">Annual Fee Leakage</span>
            <p className="text-xl font-extrabold text-red-500 mt-0.5">{formatCurrency(analysis.annual_fee_leakage)}</p>
            <span className="text-xs text-[var(--text-muted)]">Weighted Expense: {analysis.weighted_expense_ratio}% p.a.</span>
          </div>
        </div>
      </CardSurface>

      {/* Row 3: Actionable Recommendations from Analysis */}
      {analysis.recommendations && analysis.recommendations.length > 0 && (
        <div className="space-y-3">
          <SectionHeader 
            title="Actionable Rebalancing Recommendations" 
            description="Algorithmic suggestions combining holdings math and onboarding answers"
          />
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {analysis.recommendations.map((rec: any, idx: number) => (
              <CardSurface key={idx} className="p-5 border-l-[4px] border-l-teal-500 hover:shadow-md transition-all duration-300 space-y-4">
                <div className="flex justify-between items-start">
                  <span className="text-xs font-bold uppercase tracking-wider text-teal-600 bg-teal-50 px-2 py-0.5 rounded">
                    {rec.category}
                  </span>
                  <Sparkles size={14} className="text-teal-600" />
                </div>
                
                <div className="space-y-1">
                  <h4 className="font-extrabold text-sm text-[var(--text-primary)] tracking-tight">
                    {rec.title}
                  </h4>
                  <p className="text-xs text-[var(--text-muted)] leading-relaxed">
                    {rec.description}
                  </p>
                </div>

                 <Button 
                   onClick={() => handleExecuteRebalance(rec)}
                   className="w-full bg-teal-600 hover:bg-teal-700 text-[var(--text-primary)] font-bold h-9 text-xs tracking-wider uppercase rounded-sm mt-2"
                 >
                   {rec.action}
                 </Button>
              </CardSurface>
            ))}
          </div>
        </div>
      )}

      {/* Row 4: Charts Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        
        {/* Chart 1: Asset Allocation */}
        <CardSurface className="p-5 flex flex-col min-h-[380px]">
          <SectionHeader 
            title="Asset Class Distribution" 
            description="Weights breakdown across direct stocks, MFs, ETFs and Cash"
          />
          
          <div className="flex-1 w-full grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
            <div className="h-[250px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={assetAllocationData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {assetAllocationData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => formatCurrency(value)} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            
            <div className="space-y-2">
              {assetAllocationData.map((entry, idx) => (
                <div key={idx} className="flex items-center justify-between text-xs py-1 border-b border-[var(--border)]/20 last:border-b-0">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: entry.color }} />
                    <span className="font-medium text-[var(--text-muted)]">{entry.name}</span>
                  </div>
                  <div className="text-right">
                    <span className="font-bold text-[var(--text-primary)]">{entry.pct.toFixed(1)}%</span>
                    <span className="text-xs text-[var(--text-muted)] block">{formatCurrency(entry.value)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </CardSurface>

        {/* Chart 2: Top Sector Allocations */}
        <CardSurface className="p-5 flex flex-col min-h-[380px]">
          <SectionHeader 
            title="Top Sectors Exposure" 
            description="Five heaviest concentrated sectors in direct stock and mutual fund wrappers"
          />
          
          <div className="flex-1 w-full h-[250px] mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={sectorConcentrationData}
                margin={{ top: 10, right: 10, left: 10, bottom: 20 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={9} tickLine={false} axisLine={false} angle={-15} textAnchor="end" interval={0} />
                <YAxis stroke="var(--text-muted)" fontSize={9} tickLine={false} axisLine={false} tickFormatter={(v) => `₹${v/1000}k`} />
                <Tooltip formatter={(value: number) => formatCurrency(value)} />
                <Bar dataKey="value" fill="#8B6F47" radius={[4, 4, 0, 0]}>
                  {sectorConcentrationData.map((entry: any, index) => (
                    <Cell key={`cell-${index}`} fill={entry.pct > 30 ? "#EF4444" : "#14B8A6"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardSurface>
      </div>

      {/* Row 5: Detailed Holdings Table */}
      <CardSurface className="p-5">
        <SectionHeader 
          title="Consolidated Asset Holdings" 
          description="Detailed footprint telemetry from synced accounts"
        />
        
        <DataTable>
          <thead>
            <TableRow>
              <TableHead className="font-bold">Asset / Ticker</TableHead>
              <TableHead className="font-bold">Class</TableHead>
              <TableHead className="font-bold">Sector / Category</TableHead>
              <TableHead className="font-bold text-right">Shares / Units</TableHead>
              <TableHead className="font-bold text-right">Buy Price</TableHead>
              <TableHead className="font-bold text-right">Current Price</TableHead>
              <TableHead className="font-bold text-right">Current Value</TableHead>
              <TableHead className="font-bold text-right">Total P&L</TableHead>
            </TableRow>
          </thead>
          <tbody>
            {holdings.map((h: any, idx: number) => {
              const pnl = h.pnl || 0
              const pnlPct = h.pnl_pct || 0
              
              return (
                <TableRow key={idx} className="hover:bg-[var(--bg-primary)]/20 transition-colors">
                  <TableCell>
                    <div className="font-extrabold text-[var(--text-primary)]">{h.ticker || h.name}</div>
                    <div className="text-xs text-[var(--text-muted)] mt-0.5">{h.name}</div>
                  </TableCell>
                  <TableCell className="capitalize text-xs font-mono">{h.asset_type.replace("_", " ")}</TableCell>
                  <TableCell className="text-xs text-[var(--text-muted)] font-medium">
                    {h.sector || h.category || "—"}
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs">{h.shares.toLocaleString()}</TableCell>
                  <TableCell className="text-right font-mono text-xs">₹{h.avg_cost.toLocaleString()}</TableCell>
                  <TableCell className="text-right font-mono text-xs">₹{h.current_price.toLocaleString()}</TableCell>
                  <TableCell className="text-right font-mono font-bold text-xs">
                    ₹{(h.current_value || (h.shares * h.current_price)).toLocaleString()}
                  </TableCell>
                  <TableCell className={cn(
                    "text-right font-mono font-bold text-xs",
                    pnl >= 0 ? "text-teal-600" : "text-red-500"
                  )}>
                    <div>₹{pnl.toLocaleString()}</div>
                    <div className="text-xs font-medium">{pnlPct >= 0 ? "+" : ""}{pnlPct.toFixed(1)}%</div>
                  </TableCell>
                </TableRow>
              )
            })}
          </tbody>
        </DataTable>
      </CardSurface>

    </div>
  )
}
