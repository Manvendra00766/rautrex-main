"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { 
  BrainCircuit, 
  Activity, 
  Terminal, 
  ShieldAlert, 
  PieChart, 
  TrendingUp, 
  Search, 
  MousePointer2, 
  ChevronRight,
  ArrowRight,
  Check,
  X,
  Lock,
  ArrowDown,
  HelpCircle,
  Play,
  Layers,
  Sparkles
} from "lucide-react";
import { motion, useInView, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

// --- Components ---

const AnimatedCounter = ({ value, suffix = "" }: { value: string, suffix?: string }) => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true });
  const [count, setCount] = useState(0);
  const target = parseInt(value.replace(/,/g, ""));

  useEffect(() => {
    if (isInView) {
      let start = 0;
      const end = target;
      const duration = 2000;
      const increment = end / (duration / 16);
      
      const timer = setInterval(() => {
        start += increment;
        if (start >= end) {
          setCount(end);
          clearInterval(timer);
        } else {
          setCount(Math.floor(start));
        }
      }, 16);
      return () => clearInterval(timer);
    }
  }, [isInView, target]);

  return (
    <span ref={ref} className="tabular-nums">
      {count.toLocaleString()}{suffix}
    </span>
  );
};

const FeatureCard = ({ icon: Icon, title, desc, badge }: { icon: React.ComponentType<{ size?: number }>, title: string, desc: string, badge?: string }) => (
  <motion.div 
    whileHover={{ y: -4 }}
    className="glass-panel p-8 rounded-2xl group relative overflow-hidden transition-all hover:border-accent/30 bg-surface"
  >
    <div className="absolute top-0 left-0 w-1 h-0 bg-accent group-hover:h-full transition-all duration-300" />
    {badge && (
      <span className="absolute top-4 right-4 bg-[#2C2A1E] text-[#F5F0E8] border border-accent/20 text-[9px] font-bold uppercase tracking-[0.15em] px-2.5 py-1 rounded-[4px] shadow-sm z-10">
        {badge}
      </span>
    )}
    <div className="w-12 h-12 rounded-xl bg-accent/10 flex items-center justify-center text-accent mb-6 group-hover:scale-110 transition-transform">
      <Icon size={24} />
    </div>
    <h3 className="text-xl font-bold text-foreground mb-2">{title}</h3>
    <p className="text-foreground text-sm leading-relaxed mb-6">{desc}</p>
    <button 
      suppressHydrationWarning
      className="text-accent text-xs font-bold uppercase tracking-widest flex items-center gap-2 group-hover:gap-3 transition-all"
    >
      Explore <ChevronRight size={14} />
    </button>
  </motion.div>
);

// --- Mock Data ---

const TICKER_ITEMS = [
  { name: "S&P 500", ticker: "SPX", value: "5,304.72", change: "+1.2%", positive: true },
  { name: "NASDAQ", ticker: "COMP", value: "16,832.50", change: "+0.8%", positive: true },
  { name: "NIFTY 50", ticker: "NIFTY", value: "22,967.65", change: "+0.7%", positive: true },
  { name: "Apple Inc.", ticker: "AAPL", value: "$189.84", change: "+1.1%", positive: true },
  { name: "Tesla Inc.", ticker: "TSLA", value: "$179.24", change: "-0.4%", positive: false },
  { name: "Bitcoin", ticker: "BTC", value: "$68,540.20", change: "+2.4%", positive: true },
  { name: "NVIDIA Corp.", ticker: "NVDA", value: "$949.50", change: "+3.2%", positive: true }
];

interface StockResult {
  signal: string;
  fairValue: string;
  risk: string;
  action: string;
  conviction: string;
  positive: boolean;
}

const STOCK_MOCK_DATA: Record<string, StockResult> = {
  TSLA: { signal: "Bullish (82%)", fairValue: "$240", risk: "Medium", action: "Accumulate", conviction: "87%", positive: true },
  AAPL: { signal: "Strong Bullish (91%)", fairValue: "$210", risk: "Low", action: "Buy", conviction: "93%", positive: true },
  NVDA: { signal: "Very Bullish (95%)", fairValue: "$1,150", risk: "High", action: "Accumulate", conviction: "96%", positive: true },
  BTC: { signal: "Bullish (76%)", fairValue: "$72,000", risk: "High", action: "HODL", conviction: "80%", positive: true },
  MSFT: { signal: "Bullish (85%)", fairValue: "$450", risk: "Low", action: "Buy", conviction: "88%", positive: true }
};

// --- Page ---

export default function HomePage() {
  // Section 2 - Portfolio States
  const [isLinked, setIsLinked] = useState(true);

  // Section 4 - Terminal states
  const [terminalSearch, setTerminalSearch] = useState("TSLA");
  const [terminalStatus, setTerminalStatus] = useState<"idle" | "loading" | "results">("results");
  const [loadingStep, setLoadingStep] = useState(0);
  const [analyzedSymbol, setAnalyzedSymbol] = useState("TSLA");

  // Section 8 - FAQ Accordion state
  const [faqOpenIndex, setFaqOpenIndex] = useState<number | null>(null);

  const startTerminalAnalysis = (symbol: string) => {
    const sym = symbol.toUpperCase().trim();
    if (!sym) {
      setTerminalStatus("idle");
      return;
    }
    setTerminalStatus("loading");
    setLoadingStep(0);

    const steps = [
      "Scanning market data...",
      "Running ML models...",
      "Calculating risk...",
      "Generating recommendation..."
    ];

    let currentStep = 0;
    const runNextStep = () => {
      if (currentStep < steps.length - 1) {
        currentStep++;
        setLoadingStep(currentStep);
        setTimeout(runNextStep, 650);
      } else {
        setTerminalStatus("results");
        setAnalyzedSymbol(sym);
      }
    };

    setTimeout(runNextStep, 650);
  };

  const activeResult = STOCK_MOCK_DATA[analyzedSymbol] || {
    signal: "Moderate (55%)",
    fairValue: "$340",
    risk: "Medium",
    action: "Hold",
    conviction: "60%",
    positive: true
  };

  return (
    <div className="flex flex-col w-full bg-background overflow-x-hidden">
      
      {/* HERO SECTION */}
      <section className="relative min-h-screen flex items-center pt-24 pb-16 px-6 lg:px-20 overflow-hidden bg-background">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-13 gap-12 items-center z-10">
          {/* Left Content */}
          <div className="lg:col-span-8 flex flex-col gap-8">
            <motion.div 
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-[4px] bg-elevated/50 border border-border w-fit"
            >
              <div className="w-[6px] h-[6px] rounded-full bg-accent animate-pulse" />
              <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-accent">Quant Finance Platform</span>
            </motion.div>
            
            <motion.h1 
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="text-[44px] sm:text-[58px] font-bold text-foreground leading-[1.1] tracking-tighter"
            >
              Your personal hedge fund <br /> 
              <span className="text-accent">operating system</span>
            </motion.h1>

            <motion.p 
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-[16px] sm:text-[18px] text-secondary max-w-[560px] leading-[1.6]"
            >
              Institutional-grade tools for retail traders. Monte Carlo simulation, ML signals, 
              options pricing, portfolio optimization — all in one platform.
            </motion.p>

            <motion.div 
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4 pt-4"
            >
              <motion.div 
                whileHover={{ scale: 1.015 }}
                whileTap={{ scale: 0.97 }}
                className="w-full"
              >
                <Link 
                  href="/signup"
                  className="w-full block text-center bg-[#2C2A1E] hover:bg-[#2C2A1E]/90 text-[#F5F0E8] font-bold px-[28px] py-[14px] rounded-[6px] text-[13px] uppercase tracking-wider transition-all shadow-md"
                >
                  RUN YOUR FIRST SIMULATION FREE
                </Link>
              </motion.div>
            </motion.div>

            {/* Small trust badges under CTA buttons */}
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.8 }}
              transition={{ delay: 0.4 }}
              className="flex flex-wrap items-center gap-x-6 gap-y-2 mt-2 text-[10px] uppercase font-bold tracking-widest text-accent"
            >
              <span className="flex items-center gap-1.5"><ShieldAlert size={10} /> Bank-grade security</span>
              <span className="flex items-center gap-1.5"><PieChart size={10} /> Read-only broker integration</span>
              <span className="flex items-center gap-1.5"><BrainCircuit size={10} /> Data encrypted</span>
            </motion.div>
          </div>

          {/* Right Dashboard Preview */}
          <motion.div 
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4, duration: 0.6 }}
            className="lg:col-span-5 relative hidden lg:block"
          >
            <div className="relative z-10 rounded-3xl border border-border bg-[#F5F0E8] p-4 shadow-xl">
               {/* Mock Dashboard UI */}
               <div className="w-full aspect-square rounded-2xl bg-surface border border-border overflow-hidden flex flex-col shadow-inner">
                  {/* Window Title Bar */}
                  <div className="h-10 border-b border-border bg-elevated/40 flex items-center justify-between px-4">
                     <div className="flex gap-1.5">
                        <div className="w-2.5 h-2.5 rounded-full bg-negative/70" />
                        <div className="w-2.5 h-2.5 rounded-full bg-amber-500/70" />
                        <div className="w-2.5 h-2.5 rounded-full bg-positive/70" />
                     </div>
                     <span className="text-[10px] font-mono font-bold tracking-wider text-text-secondary uppercase">Rautrex Terminal v1.2</span>
                     <div className="w-8" />
                  </div>

                  {/* Dashboard Body */}
                  <div className="flex-1 p-5 flex flex-col justify-between space-y-4">
                     {/* Asset Summary */}
                     <div className="flex items-center justify-between">
                        <div>
                           <p className="text-[10px] font-mono font-bold text-text-muted uppercase tracking-wider">Active Portfolio</p>
                           <h4 className="text-xl font-bold tracking-tight text-text-primary font-mono">$1,248,590.20</h4>
                        </div>
                        <span className="bg-positive/10 text-positive text-[9px] font-bold px-2 py-0.5 rounded border border-positive/20 flex items-center gap-1">
                           <TrendingUp size={10} /> +14.8% MTD
                        </span>
                     </div>

                     {/* SVG Area Chart */}
                     <div className="h-28 w-full rounded-xl bg-elevated/40 border border-border relative overflow-hidden flex items-end">
                        {/* Chart Grid Lines */}
                        <div className="absolute inset-0 flex flex-col justify-between p-2 pointer-events-none opacity-40">
                           <div className="border-b border-border/50 w-full h-0" />
                           <div className="border-b border-border/50 w-full h-0" />
                           <div className="border-b border-border/50 w-full h-0" />
                        </div>
                        
                        {/* SVG Drawing */}
                        <svg className="w-full h-full absolute inset-0" viewBox="0 0 320 110" preserveAspectRatio="none">
                           <defs>
                              <linearGradient id="chart-gradient" x1="0" y1="0" x2="0" y2="1">
                                 <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.25" />
                                  <stop offset="100%" stopColor="var(--accent)" stopOpacity="0.0" />
                              </linearGradient>
                           </defs>
                           {/* Shadow/Fill Area */}
                           <path 
                              d="M0,110 L0,95 C40,85 60,105 100,75 C140,45 160,80 200,50 C240,20 280,35 320,10 L320,110 Z" 
                              fill="url(#chart-gradient)" 
                           />
                           {/* Stroke Path */}
                           <path 
                              d="M0,95 C40,85 60,105 100,75 C140,45 160,80 200,50 C240,20 280,35 320,10" 
                              fill="none" 
                              stroke="#2C2A1E" 
                              strokeWidth="2" 
                           />
                           {/* Today Indicator line */}
                           <line x1="200" y1="0" x2="200" y2="110" stroke="#8B6F47" strokeDasharray="3 3" strokeOpacity="0.5" />
                        </svg>

                        <span className="absolute bottom-2 left-2 text-[8px] font-mono font-bold text-text-muted bg-surface/80 border border-border px-1 py-0.5 rounded">HISTORICAL</span>
                        <span className="absolute bottom-2 right-2 text-[8px] font-mono font-bold text-accent bg-surface/80 border border-accent/20 px-1 py-0.5 rounded">FORECAST</span>
                     </div>

                     {/* Grid of Real Statistics Mockup */}
                     <div className="grid grid-cols-3 gap-3">
                        <div className="p-2.5 rounded-xl bg-elevated/40 border border-border flex flex-col justify-between">
                           <p className="text-[8px] text-text-muted font-bold uppercase tracking-wide">Return</p>
                           <h5 className="text-[13px] font-bold text-text-primary tracking-tight font-mono">+24.3%</h5>
                           <span className="text-[7px] text-positive font-bold flex items-center">▲ 1.2% TODAY</span>
                        </div>
                        <div className="p-2.5 rounded-xl bg-elevated/40 border border-border flex flex-col justify-between">
                           <p className="text-[8px] text-text-muted font-bold uppercase tracking-wide">Sharpe</p>
                           <h5 className="text-[13px] font-bold text-text-primary tracking-tight font-mono">1.87</h5>
                           <span className="text-[7px] text-accent font-bold uppercase">EFFICIENT</span>
                        </div>
                        <div className="p-2.5 rounded-xl bg-[#2C2A1E] border border-border flex flex-col justify-between">
                           <p className="text-[8px] text-[#EDE8DC]/80 font-bold uppercase tracking-wide">VaR (95%)</p>
                           <h5 className="text-[13px] font-bold text-[#F5F0E8] tracking-tight font-mono">2.1%</h5>
                           <span className="text-[7px] text-positive font-bold uppercase">OPTIMAL</span>
                        </div>
                     </div>
                  </div>
               </div>

               {/* Floating Cards */}
               <motion.div 
                animate={{ y: [0, -6, 0] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                className="absolute -top-6 -left-12 glass-panel p-3.5 rounded-xl border border-accent/30 shadow-md bg-surface"
               >
                  <p className="text-[8px] text-text-muted font-bold uppercase mb-0.5 tracking-wider">Portfolio Return</p>
                  <p className="text-md font-bold tracking-tight text-text-primary font-mono">+24.3%</p>
               </motion.div>

               <motion.div 
                animate={{ y: [0, 6, 0] }}
                transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
                className="absolute top-1/3 -right-8 glass-panel p-3.5 rounded-xl border border-accent/30 shadow-md bg-surface"
               >
                  <p className="text-[8px] text-text-muted font-bold uppercase mb-0.5 tracking-wider">Sharpe Ratio</p>
                  <p className="text-md font-bold tracking-tight text-accent font-mono">1.87</p>
               </motion.div>

               <motion.div 
                animate={{ x: [0, -6, 0] }}
                transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
                className="absolute -bottom-8 left-12 glass-panel p-3.5 rounded-xl border border-border shadow-md bg-surface"
               >
                  <p className="text-[8px] text-text-muted font-bold uppercase mb-0.5 tracking-wider">VaR (95%)</p>
                  <p className="text-md font-bold tracking-tight text-text-primary font-mono">2.1%</p>
               </motion.div>
            </div>
            
            {/* Ambient Light */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-accent/15 rounded-full blur-[100px] -z-10" />
          </motion.div>
        </div>
      </section>

      {/* SECTION 1 — LIVE MARKET TICKER STRIP */}
      <section className="px-6 lg:px-20 -mt-6 mb-16 relative z-20 overflow-hidden">
        <div className="max-w-7xl mx-auto bg-surface border border-border rounded-full py-4 px-6 shadow-sm overflow-hidden flex items-center">
          <div className="w-full overflow-hidden flex items-center relative custom-scrollbar">
            <div className="absolute left-0 top-0 bottom-0 w-16 bg-gradient-to-r from-surface to-transparent z-10 pointer-events-none" />
            <div className="absolute right-0 top-0 bottom-0 w-16 bg-gradient-to-l from-surface to-transparent z-10 pointer-events-none" />
            
            <motion.div 
              animate={{ x: ["0%", "-50%"] }}
              transition={{ repeat: Infinity, duration: 25, ease: "linear" }}
              className="flex gap-12 whitespace-nowrap w-max pr-12"
            >
              {[...TICKER_ITEMS, ...TICKER_ITEMS].map((item, index) => (
                <div key={index} className="flex items-center gap-3 font-mono text-[13px] bg-elevated/40 px-4 py-1.5 rounded-full border border-border/50">
                  {/* Pulse Indicator */}
                  <span className={cn(
                    "w-2 h-2 rounded-full",
                    item.positive ? "bg-positive animate-pulse shadow-[0_0_8px_rgba(22,101,52,0.8)]" : "bg-negative animate-pulse shadow-[0_0_8px_rgba(153,27,27,0.8)]"
                  )} />
                  <span className="font-bold text-foreground">{item.ticker}</span>
                  <span className="text-secondary">{item.value}</span>
                  <span className={cn(
                    "font-bold font-mono text-[12px] flex items-center gap-0.5",
                    item.positive ? "text-positive" : "text-negative"
                  )}>
                    {item.positive ? "▲" : "▼"} {item.change}
                  </span>
                </div>
              ))}
            </motion.div>
          </div>
        </div>
      </section>

      {/* STATS SECTION */}
      <section className="bg-surface border-y border-border py-12">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8">
          {[
            { label: "Global Tickers", value: "50,000", suffix: "+" },
            { label: "Quant Models", value: "10", suffix: "+" },
            { label: "Data Quality", value: "Real-time", isText: true },
            { label: "Pricing", value: "Free to Start", isText: true }
          ].map((stat, i) => (
            <div key={i} className="text-center space-y-1">
              <p className="text-3xl md:text-4xl font-black text-[#795548]">
                {stat.isText ? stat.value : <AnimatedCounter value={stat.value} suffix={stat.suffix} />}
              </p>
              <p className="text-[10px] md:text-xs font-bold text-[#795548]/85 uppercase tracking-[0.2em]">{stat.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* SECTION 2 — PORTFOLIO INTELLIGENCE PREVIEW */}
      <section className="py-24 px-6 lg:px-20 relative">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
            <div className="space-y-4">
              <h2 className="text-accent text-xs font-black uppercase tracking-[0.3em]">Module Showcase</h2>
              <h2 className="text-4xl md:text-5xl font-bold text-foreground tracking-tight">AI Portfolio Intelligence</h2>
              <p className="text-black font-medium leading-relaxed max-w-xl">
                Get a deep diagnostics report of your portfolio risk parameters and dynamic rebalancing opportunities in real-time.
              </p>
            </div>

            {/* Interactive Toggle for Linked / Empty state */}
            <div className="flex items-center bg-elevated/80 border border-border rounded-full p-1 self-start md:self-auto shadow-sm">
              <button 
                suppressHydrationWarning
                onClick={() => setIsLinked(true)}
                className={cn(
                  "px-4 py-2 rounded-full text-xs font-bold uppercase tracking-wider transition-all",
                  isLinked ? "bg-[#2C2A1E] text-[#F5F0E8] shadow-md" : "text-text-muted hover:text-foreground"
                )}
              >
                Connected Demo
              </button>
              <button 
                suppressHydrationWarning
                onClick={() => setIsLinked(false)}
                className={cn(
                  "px-4 py-2 rounded-full text-xs font-bold uppercase tracking-wider transition-all",
                  !isLinked ? "bg-[#2C2A1E] text-[#F5F0E8] shadow-md" : "text-text-muted hover:text-foreground"
                )}
              >
                Unlinked State
              </button>
            </div>
          </div>

          {/* Large Premium Dashboard Card */}
          <div className="relative rounded-[28px] border border-border bg-[#F5F0E8]/50 p-6 md:p-10 shadow-lg overflow-hidden min-h-[500px]">
            
            <AnimatePresence mode="wait">
              {isLinked ? (
                <motion.div 
                  key="linked"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.4 }}
                  className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center"
                >
                  {/* Left stats */}
                  <div className="lg:col-span-5 space-y-6">
                    <div className="p-6 rounded-[20px] bg-surface border border-border shadow-sm space-y-5">
                      <div className="flex justify-between items-center pb-3 border-b border-border/60">
                        <span className="text-xs font-bold uppercase tracking-widest text-text-muted">Portfolio Health Score</span>
                        <span className="font-mono text-2xl font-black text-accent">84/100</span>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        {[
                          { label: "Risk Level", val: "Moderate", highlight: "text-[#D97706]" },
                          { label: "Diversification", val: "Good", highlight: "text-positive" },
                          { label: "Expected Return", val: "17.2%", highlight: "text-positive font-mono" },
                          { label: "Volatility", val: "Medium", highlight: "text-[#D97706]" }
                        ].map((stat, i) => (
                          <div key={i} className="bg-elevated/40 border border-border/40 rounded-xl p-3">
                            <span className="text-[9px] font-bold uppercase tracking-wider text-text-secondary block mb-1">{stat.label}</span>
                            <span className={cn("text-[14px] font-bold uppercase tracking-tight", stat.highlight)}>{stat.val}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Right side circular gauge + recommendation box */}
                  <div className="lg:col-span-7 grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
                    {/* Gauge */}
                    <div className="flex flex-col items-center justify-center p-6 bg-surface border border-border rounded-[20px] shadow-sm">
                      <div className="relative w-40 h-40 flex items-center justify-center">
                        {/* SVG Gauge */}
                        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                          <circle cx="50" cy="50" r="40" stroke="var(--border)" strokeWidth="8" fill="transparent" className="opacity-30" />
                          <motion.circle 
                            cx="50" 
                            cy="50" 
                            r="40" 
                            stroke="var(--accent)" 
                            strokeWidth="8" 
                            fill="transparent" 
                            strokeDasharray="251.2"
                            initial={{ strokeDashoffset: 251.2 }}
                            animate={{ strokeDashoffset: 251.2 - (251.2 * 84) / 100 }}
                            transition={{ duration: 1.5, ease: "easeOut" }}
                          />
                        </svg>
                        <div className="absolute flex flex-col items-center">
                          <span className="text-3xl font-black font-mono text-foreground">84</span>
                          <span className="text-[10px] font-bold tracking-widest text-text-muted uppercase">EXCELLENT</span>
                        </div>
                      </div>
                      <span className="text-[11px] font-bold uppercase tracking-widest text-accent mt-4">AI Score Optimization</span>
                    </div>

                    {/* Recommendations box */}
                    <div className="p-6 bg-surface border border-border rounded-[20px] shadow-sm space-y-4">
                      <div className="flex items-center gap-2 text-accent pb-2 border-b border-border/60">
                        <BrainCircuit size={16} />
                        <span className="text-[10px] font-bold uppercase tracking-widest">AI Action Directives</span>
                      </div>
                      
                      <ul className="space-y-3.5">
                        {[
                          "Reduce Tech exposure by 8%",
                          "Increase Healthcare allocation by 5%",
                          "Risk adjusted return can improve by 12%"
                        ].map((rec, idx) => (
                          <li key={idx} className="flex gap-2.5 items-start text-xs font-medium text-foreground">
                            <span className="mt-0.5 w-4 h-4 rounded-full bg-accent/15 flex items-center justify-center text-accent shrink-0 text-[10px] font-bold">{idx + 1}</span>
                            <span>{rec}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </motion.div>
              ) : (
                <motion.div 
                  key="unlinked"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.4 }}
                  className="absolute inset-0 flex flex-col items-center justify-center p-8 text-center bg-surface/60 backdrop-blur-md rounded-[28px] z-10"
                >
                  <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center text-accent mb-6 border border-accent/20">
                    <Lock size={28} />
                  </div>
                  <h3 className="text-2xl font-bold text-foreground tracking-tight mb-2">Connect portfolio to unlock insights</h3>
                  <p className="text-secondary max-w-sm text-sm leading-relaxed mb-6 font-medium">
                    Link your brokerage securely to evaluate key Sharpe values, tail risk calculations, and real-time optimization weightings.
                  </p>
                  
                  <motion.button 
                    suppressHydrationWarning
                    whileHover={{ scale: 1.015 }}
                    whileTap={{ scale: 0.97 }}
                    onClick={() => setIsLinked(true)}
                    className="bg-[#2C2A1E] text-[#F5F0E8] text-xs font-bold uppercase tracking-widest px-8 py-3.5 rounded-lg shadow-md hover:bg-[#2C2A1E]/95 transition-all"
                  >
                    Simulate Integration Demo
                  </motion.button>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Floating Metric Cards (Sharp, VaR, Alpha) */}
            <AnimatePresence>
              {isLinked && (
                <>
                  <motion.div 
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0 }}
                    className="absolute -top-3 left-4 hidden lg:block glass-panel px-4 py-2.5 rounded-xl border border-accent/30 shadow-md bg-surface"
                  >
                    <span className="text-[8px] font-bold text-text-muted uppercase tracking-wider block">Sharpe Ratio</span>
                    <span className="text-sm font-mono font-black text-accent">1.87</span>
                  </motion.div>

                  <motion.div 
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0 }}
                    className="absolute bottom-6 left-12 hidden lg:block glass-panel px-4 py-2.5 rounded-xl border border-border shadow-md bg-surface"
                  >
                    <span className="text-[8px] font-bold text-text-muted uppercase tracking-wider block">VaR (95%)</span>
                    <span className="text-sm font-mono font-black text-foreground">2.1%</span>
                  </motion.div>

                  <motion.div 
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0 }}
                    className="absolute top-1/2 -right-4 hidden lg:block glass-panel px-4 py-2.5 rounded-xl border border-accent/30 shadow-md bg-surface"
                  >
                    <span className="text-[8px] font-bold text-text-muted uppercase tracking-wider block">Alpha Generation</span>
                    <span className="text-sm font-mono font-black text-positive">+4.2%</span>
                  </motion.div>
                </>
              )}
            </AnimatePresence>

          </div>

          {/* PREMIUM PORTFOLIO CTA CARD */}
          <motion.div 
            whileHover={{ y: -2 }}
            className="w-full border border-dashed border-accent/40 rounded-[24px] bg-surface p-8 text-center relative overflow-hidden flex flex-col md:flex-row items-center justify-between gap-6 shadow-sm hover:border-accent/80 transition-all duration-300"
          >
            <div className="text-left space-y-1.5 max-w-xl">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-accent/10 border border-accent/20 text-[9px] font-bold uppercase tracking-wider text-accent w-fit mb-1">
                <Sparkles size={9} /> Automated Portfolio Scanner
              </span>
              <h3 className="text-xl md:text-2xl font-bold text-foreground tracking-tight">Connect your portfolio</h3>
              <p className="text-secondary text-sm font-medium leading-relaxed">
                Get personalized AI-driven risk and optimization insights. View factor exposures and simulate stressors instantly.
              </p>
            </div>
            
            <div className="flex flex-col items-center gap-2">
              <motion.div 
                whileHover={{ scale: 1.015 }}
                whileTap={{ scale: 0.97 }}
                className="shrink-0"
              >
                <Link 
                  href="/signup"
                  className="inline-block bg-[#2C2A1E] text-[#F5F0E8] font-bold px-8 py-4 rounded-lg text-xs uppercase tracking-wider shadow-md hover:bg-[#2C2A1E]/90 transition-all"
                >
                  Start Free Analysis
                </Link>
              </motion.div>
              <span className="text-[8px] uppercase tracking-widest text-text-muted font-bold">100% SECURE • READ-ONLY</span>
            </div>
          </motion.div>

        </div>
      </section>

      {/* SECTION 3 — WHY RAUTREX COMPARISON */}
      <section id="why-us" className="py-24 px-6 lg:px-20 bg-elevated/10 relative">
        <div className="max-w-7xl mx-auto space-y-16">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <h2 className="text-accent text-xs font-black uppercase tracking-[0.3em]">Market Shift</h2>
            <h2 className="text-4xl md:text-5xl font-bold text-foreground tracking-tight">Why investors switch to RAUTREX</h2>
            <p className="text-black font-medium leading-relaxed">
              We replace fragmented manual workflows with dynamic institutional algorithms, engineered for individual success.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-stretch">
            
            {/* Traditional Card */}
            <motion.div 
              whileHover={{ y: -4 }}
              className="rounded-[24px] border border-border bg-surface/50 p-8 flex flex-col justify-between shadow-sm group hover:bg-surface transition-all duration-300"
            >
              <div className="space-y-6">
                <div className="flex items-center justify-between pb-4 border-b border-border/60">
                  <h4 className="text-lg font-bold text-secondary uppercase tracking-widest">Traditional Investing</h4>
                  <div className="w-8 h-8 rounded-full bg-negative/10 flex items-center justify-center text-negative">
                    <X size={16} />
                  </div>
                </div>

                <ul className="space-y-4">
                  {[
                    { text: "Manual research", desc: "Sifting through PDFs, outdated screens, and disorganized balance sheets." },
                    { text: "Multiple tools", desc: "Paying thousands annually for multiple platforms to track basic data feeds." },
                    { text: "Emotional decisions", desc: "Buying at market peaks and panic selling during volatile drops." },
                    { text: "Static portfolio", desc: "Weights remain constant despite dynamic shifts in index volatility and yields." }
                  ].map((pt, i) => (
                    <li key={i} className="flex gap-4 items-start">
                      <div className="mt-1 w-4 h-4 rounded-full bg-negative/15 flex items-center justify-center text-negative shrink-0">
                        <span className="w-1.5 h-1.5 rounded-full bg-negative" />
                      </div>
                      <div>
                        <h5 className="text-sm font-bold text-foreground">{pt.text}</h5>
                        <p className="text-xs text-secondary mt-0.5 leading-relaxed">{pt.desc}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </motion.div>

            {/* RAUTREX Card */}
            <motion.div 
              whileHover={{ y: -4 }}
              className="rounded-[24px] border-2 border-accent bg-surface p-8 flex flex-col justify-between shadow-md relative overflow-hidden"
            >
              {/* Corner Ribbon */}
              <div className="absolute top-0 right-0 bg-accent text-[#F5F0E8] text-[8px] font-black uppercase tracking-[0.2em] px-4 py-1.5 rounded-bl shadow-sm">
                Next-Gen Terminal
              </div>

              <div className="space-y-6">
                <div className="flex items-center justify-between pb-4 border-b border-border/60">
                  <h4 className="text-lg font-bold text-accent uppercase tracking-widest">RAUTREX Terminal</h4>
                  <div className="w-8 h-8 rounded-full bg-accent/15 flex items-center justify-center text-accent">
                    <Check size={16} />
                  </div>
                </div>

                <ul className="space-y-4">
                  {[
                    { text: "AI-powered analysis", desc: "Continuous machine learning pipelines scanning technical levels and valuations." },
                    { text: "One unified dashboard", desc: "Integrate Monte Carlo scenarios, backtesters, and pricing models into a single tab." },
                    { text: "Data-driven decisions", desc: "Algorithmic factor evaluations eliminate human sentiment errors." },
                    { text: "Dynamic optimization", desc: "Automated Efficient Frontier recalculations adjust weights dynamically." }
                  ].map((pt, i) => (
                    <li key={i} className="flex gap-4 items-start">
                      <div className="mt-1 w-4 h-4 rounded-full bg-accent/20 flex items-center justify-center text-accent shrink-0">
                        <Check size={10} className="stroke-[3]" />
                      </div>
                      <div>
                        <h5 className="text-sm font-bold text-foreground">{pt.text}</h5>
                        <p className="text-xs text-secondary mt-0.5 leading-relaxed">{pt.desc}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </motion.div>

          </div>
        </div>
      </section>

      {/* SECTION 4 — INTERACTIVE TERMINAL DEMO */}
      <section id="terminal" className="py-24 px-6 lg:px-20 relative">
        <div className="max-w-7xl mx-auto space-y-16">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <h2 className="text-accent text-xs font-black uppercase tracking-[0.3em]">Algorithmic Simulator</h2>
            <h2 className="text-4xl md:text-5xl font-bold text-foreground tracking-tight">Try the RAUTREX Terminal</h2>
            <p className="text-black font-medium leading-relaxed">
              Test drive our ML signal models below. Enter any stock symbol or select from standard presets to view diagnostic compilation logic.
            </p>
          </div>

          {/* Terminal card looks like a real institutional trading terminal */}
          <div className="rounded-[28px] border border-border bg-[#F5F0E8] p-4 md:p-6 shadow-xl max-w-4xl mx-auto">
            <div className="w-full bg-[#1A1714] text-[#EDE8DC] rounded-2xl overflow-hidden shadow-inner flex flex-col min-h-[460px]">
              
              {/* Terminal Window Header */}
              <div className="bg-[#2C2A1E] px-4 py-3 flex items-center justify-between border-b border-border/20">
                <div className="flex gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-negative/80" />
                  <div className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
                  <div className="w-2.5 h-2.5 rounded-full bg-positive/80" />
                </div>
                <span className="text-[10px] font-mono tracking-widest text-[#EDE8DC]/50 uppercase font-bold">RAUTREX QUANT ENGINE v1.2</span>
                <span className="text-[10px] font-mono text-accent">SECURE CORE</span>
              </div>

              {/* Terminal Inner Grid */}
              <div className="flex-1 p-6 flex flex-col justify-between gap-6">
                
                {/* Search controls */}
                <div className="space-y-4">
                  <div className="flex flex-col md:flex-row items-stretch md:items-center gap-3">
                    <div className="relative flex-1">
                      <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#EDE8DC]/40" size={16} />
                      <input 
                        suppressHydrationWarning
                        type="text"
                        value={terminalSearch}
                        onChange={(e) => {
                          setTerminalSearch(e.target.value);
                          if (!e.target.value.trim()) setTerminalStatus("idle");
                        }}
                        placeholder="Search stock symbol... (e.g. AAPL, NVDA)"
                        className="w-full bg-[#2C2A1E]/60 border border-border/20 rounded-lg py-2.5 pl-10 pr-4 text-sm font-mono text-[#F5F0E8] placeholder-[#EDE8DC]/30 focus:outline-none focus:border-accent/60 transition-colors"
                        onKeyDown={(e) => {
                          if (e.key === "Enter") startTerminalAnalysis(terminalSearch);
                        }}
                      />
                    </div>
                    
                    <motion.button 
                      suppressHydrationWarning
                      whileHover={{ scale: 1.015 }}
                      whileTap={{ scale: 0.97 }}
                      onClick={() => startTerminalAnalysis(terminalSearch)}
                      className="bg-accent text-[#F5F0E8] px-6 py-2.5 rounded-lg text-xs uppercase font-mono tracking-wider font-bold transition-all hover:bg-accent/90 flex items-center justify-center gap-2"
                    >
                      <Play size={10} className="fill-[#F5F0E8]" /> Analyze Stock
                    </motion.button>
                  </div>

                  {/* Preset chips */}
                  <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-[#EDE8DC]/60">
                    <span className="text-[10px] uppercase font-bold tracking-wider mr-1 text-[#EDE8DC]/40">Quick presets:</span>
                    {["TSLA", "AAPL", "NVDA", "BTC", "MSFT"].map((chip) => (
                      <button 
                        suppressHydrationWarning
                        key={chip} 
                        onClick={() => {
                          setTerminalSearch(chip);
                          startTerminalAnalysis(chip);
                        }}
                        className={cn(
                          "px-2.5 py-1 rounded bg-[#2C2A1E]/80 border transition-all",
                          analyzedSymbol === chip && terminalStatus === "results" 
                            ? "border-accent text-accent font-bold bg-accent/10" 
                            : "border-border/10 hover:border-accent/40 hover:text-accent"
                        )}
                      >
                        {chip}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Main Content Area based on Status */}
                <div className="flex-1 rounded-xl bg-[#2C2A1E]/30 border border-border/10 p-5 flex flex-col justify-center min-h-[220px]">
                  <AnimatePresence mode="wait">
                    
                    {/* Empty State */}
                    {terminalStatus === "idle" && (
                      <motion.div 
                        key="idle"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="text-center py-8 space-y-2"
                      >
                        <Search size={32} className="mx-auto text-accent opacity-50" />
                        <p className="text-sm font-mono text-accent">Enter a symbol to analyze</p>
                        <p className="text-xs text-[#EDE8DC]/40 max-w-xs mx-auto">Query real-time probability weightings from our multi-factor engine.</p>
                      </motion.div>
                    )}

                    {/* Diagnostic Loading State */}
                    {terminalStatus === "loading" && (
                      <motion.div 
                        key="loading"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="font-mono text-xs space-y-2.5 text-left md:pl-10"
                      >
                        {[
                          "Scanning market data...",
                          "Running ML models...",
                          "Calculating risk...",
                          "Generating recommendation..."
                        ].map((step, idx) => (
                          <div key={idx} className="flex items-center gap-3">
                            <span className={cn(
                              "w-1.5 h-1.5 rounded-full shrink-0",
                              loadingStep > idx ? "bg-positive" : loadingStep === idx ? "bg-accent animate-pulse" : "bg-[#EDE8DC]/10"
                            )} />
                            <span className={cn(
                              loadingStep === idx ? "text-accent font-bold" : loadingStep > idx ? "text-positive" : "text-[#EDE8DC]/20"
                            )}>
                              {step}
                            </span>
                            {loadingStep === idx && <span className="animate-pulse">_</span>}
                            {loadingStep > idx && <span className="text-positive font-bold ml-auto font-mono text-[10px]">SUCCESS</span>}
                          </div>
                        ))}
                      </motion.div>
                    )}

                    {/* Results Render */}
                    {terminalStatus === "results" && (
                      <motion.div 
                        key="results"
                        initial={{ opacity: 0, scale: 0.99 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0 }}
                        className="grid grid-cols-2 md:grid-cols-3 gap-6 font-mono"
                      >
                        <div className="col-span-2 md:col-span-3 border-b border-border/10 pb-3 flex justify-between items-center">
                          <span className="text-sm font-bold uppercase tracking-wider text-accent font-mono">QUANTIATIVE AUDIT REPORT: {analyzedSymbol}</span>
                          <span className="text-[10px] text-positive font-bold bg-positive/10 px-2 py-0.5 rounded border border-positive/20 flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-positive animate-pulse" /> LIVE STREAMING
                          </span>
                        </div>

                        {[
                          { label: "Signal Type", value: activeResult.signal, color: "text-positive font-bold" },
                          { label: "Calculated Fair Value", value: activeResult.fairValue, color: "text-foreground font-bold" },
                          { label: "Vol Risk Bracket", value: activeResult.risk, color: "text-[#D97706]" },
                          { label: "Suggested Weight Action", value: activeResult.action, color: "text-positive font-bold" },
                          { label: "Algorithm Conviction", value: activeResult.conviction, color: "text-accent font-bold" },
                          { label: "Diagnostic Accuracy", value: "99.8%", color: "text-secondary" }
                        ].map((stat, i) => (
                          <div key={i} className="bg-[#2C2A1E]/50 border border-border/10 p-3 rounded-lg flex flex-col justify-between">
                            <span className="text-[8px] text-[#EDE8DC]/40 uppercase tracking-widest block mb-1">{stat.label}</span>
                            <span className={cn("text-xs md:text-sm font-bold tracking-tight", stat.color)}>{stat.value}</span>
                          </div>
                        ))}
                      </motion.div>
                    )}

                  </AnimatePresence>
                </div>

                {/* Footer status text */}
                <div className="flex flex-wrap items-center justify-between text-[9px] font-mono text-[#EDE8DC]/30 border-t border-border/10 pt-3">
                  <span>AES-256 SECURED CONNECTION</span>
                  <span>LATENCY: 14ms</span>
                  <span>SERVER ID: SG-CORE-2</span>
                </div>

              </div>

            </div>
          </div>

        </div>
      </section>

      {/* SECTION 5 — TRUST / SOCIAL PROOF */}
      <section className="py-24 px-6 lg:px-20 bg-surface border-y border-border">
        <div className="max-w-7xl mx-auto space-y-16">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <h2 className="text-accent text-xs font-black uppercase tracking-[0.3em]">Hedge Scale</h2>
            <h2 className="text-4xl md:text-5xl font-bold text-foreground tracking-tight">Engineered for institutional scale</h2>
            <p className="text-black font-medium leading-relaxed">
              We process millions of quantitative updates daily, delivering sub-millisecond mathematical analysis to our global users.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
            {[
              { label: "Simulations Run", value: "10,000", suffix: "+" },
              { label: "Active Users", value: "500", suffix: "+" },
              { label: "Data Points Processed", value: "50,000,000", suffix: "+" },
              { label: "User Satisfaction", value: "95", suffix: "%" }
            ].map((card, i) => (
              <motion.div 
                key={i} 
                whileHover={{ y: -4 }}
                className="bg-surface border border-border rounded-[20px] p-6 text-center space-y-2 shadow-sm relative overflow-hidden transition-all duration-300 hover:border-accent/40"
              >
                <div className="absolute top-0 left-0 w-full h-[3px] bg-accent/15" />
                <p className="text-4xl md:text-5xl font-mono font-black text-accent tracking-tighter">
                  <AnimatedCounter value={card.value} suffix={card.suffix} />
                </p>
                <p className="text-[10px] md:text-xs font-bold text-secondary uppercase tracking-[0.2em]">{card.label}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* SECTION 6 — HOW RAUTREX THINKS */}
      <section className="py-24 px-6 lg:px-20 bg-elevated/10 relative">
        <div className="max-w-7xl mx-auto space-y-16">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <h2 className="text-accent text-xs font-black uppercase tracking-[0.3em]">The Data Flow</h2>
            <h2 className="text-4xl md:text-5xl font-bold text-foreground tracking-tight">How RAUTREX Thinks</h2>
            <p className="text-black font-medium leading-relaxed">
              A highly optimized pipeline translating raw financial feeds into high-conviction decision recommends.
            </p>
          </div>

          {/* flowchart visual grid */}
          <div className="flex flex-col lg:flex-row items-center justify-between gap-6 max-w-5xl mx-auto relative">
            
            {[
              { title: "Market Data", desc: "Real-time pricing feeds & fundamentals ingest.", icon: Layers },
              { title: "AI Analysis", desc: "Machine learning forecasting & sentiment filters.", icon: BrainCircuit },
              { title: "Risk Engine", desc: "Monte Carlo stress modeling & VaR calculation.", icon: Activity },
              { title: "Portfolio Optimization", desc: "Optimal asset weight frontier distribution.", icon: PieChart },
              { title: "Decision Recommendation", desc: "Institutional direct buys & risk adjustment targets.", icon: Terminal }
            ].map((step, idx, arr) => {
              const StepIcon = step.icon;
              return (
                <div key={idx} className="flex flex-col lg:flex-row items-center w-full lg:w-auto relative">
                  
                  {/* Step Card */}
                  <motion.div 
                    whileHover={{ y: -4 }}
                    className="w-full lg:w-[170px] bg-surface border border-border rounded-[20px] p-5 text-center shadow-sm z-10 transition-all duration-300 hover:border-accent/40"
                  >
                    <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center text-accent mx-auto mb-4 border border-accent/20">
                      <StepIcon size={18} />
                    </div>
                    <span className="text-[10px] font-bold text-accent uppercase tracking-widest block mb-1">Step {idx + 1}</span>
                    <h4 className="text-sm font-bold text-foreground tracking-tight mb-2">{step.title}</h4>
                    <p className="text-[11px] text-secondary leading-normal">{step.desc}</p>
                  </motion.div>

                  {/* Flow Arrow (not on last item) */}
                  {idx < arr.length - 1 && (
                    <div className="my-4 lg:my-0 lg:mx-3 text-accent/30 shrink-0">
                      <ArrowRight size={24} className="hidden lg:block animate-pulse" />
                      <ArrowDown size={24} className="lg:hidden animate-pulse" />
                    </div>
                  )}

                </div>
              );
            })}

          </div>
        </div>
      </section>

      {/* FEATURES SECTION */}
      <section id="features" className="py-32 px-6 lg:px-20 relative">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-3xl mx-auto mb-20 space-y-4">
            <h2 className="text-accent text-xs font-black uppercase tracking-[0.3em]">Institutional Grade</h2>
            <h2 className="text-4xl md:text-5xl font-bold text-foreground tracking-tight">Powerful modules for every edge</h2>
            <p className="text-black leading-relaxed font-medium">
              We&apos;ve consolidated professional tools that usually cost thousands of dollars into a single, seamless experience.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <FeatureCard 
              icon={Activity} 
              title="Monte Carlo Simulation" 
              desc="Run 10,000 scenarios in seconds to model potential portfolio outcomes and tail risks." 
            />
            <FeatureCard 
              icon={BrainCircuit} 
              title="ML Signal Engine" 
              desc="LSTM + XGBoost + Sentiment analysis. Our ensemble model gives you high-conviction signals." 
              badge="Fan Favorite"
            />
            <FeatureCard 
              icon={Terminal} 
              title="Strategy Backtester" 
              desc="Test any technical or quant strategy against 10+ years of high-fidelity historical data." 
            />
            <FeatureCard 
              icon={PieChart} 
              title="Portfolio Optimizer" 
              desc="Modern Portfolio Theory made easy. Markowitz Efficient Frontier, Risk Parity, and more." 
            />
            <FeatureCard 
              icon={TrendingUp} 
              title="Options Pricer" 
              desc="Professional options analytics. Black-Scholes, Binomial models, and IV surface visualization." 
            />
            <FeatureCard 
              icon={ShieldAlert} 
              title="Risk Analytics" 
              desc="Stay protected with VaR, CVaR, Stress Testing, and detailed Factor Exposure analysis." 
            />
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how-it-works" className="py-32 px-6 lg:px-20 bg-elevated/30">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-20 space-y-3">
             <h2 className="text-accent text-xs font-black uppercase tracking-[0.3em]">How It Works</h2>
             <h2 className="text-4xl md:text-5xl font-bold text-foreground tracking-tight">Simple three-step workflow</h2>
             <p className="text-foreground leading-relaxed font-medium max-w-xl mx-auto">From discovery to execution in minutes — not days.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
             {/* Connection Arrows (Desktop) */}
             <div className="hidden md:block absolute top-24 left-1/3 -translate-x-1/2 text-accent/20 z-20">
                <ArrowRight size={40} />
             </div>
             <div className="hidden md:block absolute top-24 left-2/3 -translate-x-1/2 text-accent/20 z-20">
                <ArrowRight size={40} />
             </div>

             {/* Step 1: Search */}
             <div className="flex flex-col items-center text-center space-y-6">
                <div className="w-20 h-20 rounded-3xl bg-background border border-border flex items-center justify-center text-accent">
                   <Search size={32} />
                </div>
                <div className="space-y-2">
                   <h4 className="text-xl font-bold text-foreground">Search any stock</h4>
                   <p className="text-foreground text-sm leading-relaxed max-w-xs font-medium">Access 50,000+ global tickers with deep fundamentals and real-time data.</p>
                </div>
                {/* Mini Mockup: Search UI */}
                <div className="w-full max-w-[280px] rounded-2xl border border-border bg-surface p-4 shadow-lg space-y-3">
                   <div className="flex items-center gap-2 bg-elevated/40 border border-border rounded-lg px-3 py-2.5">
                     <Search size={14} className="text-foreground" />
                     <span className="text-[11px] text-foreground font-mono">Search ticker or name...</span>
                   </div>
                   <div className="space-y-1.5">
                     {[{ t: 'AAPL', n: 'Apple Inc.', p: '$189.84', c: '+1.23%' }, { t: 'NVDA', n: 'NVIDIA Corp', p: '$945.10', c: '+4.12%' }, { t: 'MSFT', n: 'Microsoft', p: '$420.55', c: '+0.87%' }].map((s, i) => (
                       <div key={i} className={cn("flex items-center justify-between px-3 py-2 rounded-lg transition-colors", i === 0 ? "bg-accent/10 border border-accent/20" : "hover:bg-elevated/40")}>
                         <div className="flex flex-col">
                           <span className="text-[11px] font-bold text-text-primary font-mono">{s.t}</span>
                           <span className="text-[9px] text-foreground">{s.n}</span>
                         </div>
                         <div className="flex flex-col items-end">
                           <span className="text-[10px] font-bold text-text-primary font-mono">{s.p}</span>
                           <span className="text-[9px] font-bold text-positive">{s.c}</span>
                         </div>
                       </div>
                     ))}
                   </div>
                </div>
             </div>

             {/* Step 2: Run Analysis */}
             <div className="flex flex-col items-center text-center space-y-6">
                <div className="w-20 h-20 rounded-3xl bg-background border border-border flex items-center justify-center text-accent">
                   <BrainCircuit size={32} />
                </div>
                <div className="space-y-2">
                   <h4 className="text-xl font-bold text-foreground">Run analysis</h4>
                   <p className="text-foreground text-sm leading-relaxed max-w-xs font-medium">Select your modules. Run simulations, train models, or optimize weights.</p>
                </div>
                {/* Mini Mockup: Analysis Panel */}
                <div className="w-full max-w-[280px] rounded-2xl border border-border bg-surface p-4 shadow-lg space-y-3">
                   <div className="flex items-center justify-between">
                     <span className="text-[10px] font-bold text-foreground uppercase tracking-wider">AAPL — Models</span>
                     <span className="text-[9px] font-bold text-positive bg-positive/10 px-1.5 py-0.5 rounded border border-positive/20">RUNNING</span>
                   </div>
                   {[{ name: 'Monte Carlo', pct: 100 }, { name: 'ML Ensemble', pct: 78 }, { name: 'DCF Valuation', pct: 45 }].map((m, i) => (
                     <div key={i} className="space-y-1">
                       <div className="flex items-center justify-between">
                         <span className="text-[10px] font-medium text-text-primary">{m.name}</span>
                         <span className="text-[9px] font-mono font-bold text-accent">{m.pct}%</span>
                       </div>
                       <div className="w-full h-1.5 rounded-full bg-elevated/40 overflow-hidden">
                         <div className="h-full rounded-full bg-accent/70 transition-all" style={{ width: `${m.pct}%` }} />
                       </div>
                     </div>
                   ))}
                   <div className="pt-1 border-t border-border">
                     <div className="flex items-center gap-1.5">
                       <div className="w-1.5 h-1.5 rounded-full bg-positive animate-pulse" />
                       <span className="text-[9px] text-foreground font-medium">Processing 10,000 simulations...</span>
                     </div>
                   </div>
                </div>
             </div>

             {/* Step 3: Make Decisions */}
             <div className="flex flex-col items-center text-center space-y-6">
                <div className="w-20 h-20 rounded-3xl bg-background border border-border flex items-center justify-center text-accent">
                   <MousePointer2 size={32} />
                </div>
                <div className="space-y-2">
                   <h4 className="text-xl font-bold text-foreground">Make decisions</h4>
                   <p className="text-foreground text-sm leading-relaxed max-w-xs font-medium">Execute trades with institutional conviction and managed risk parameters.</p>
                </div>
                {/* Mini Mockup: Decision Summary */}
                <div className="w-full max-w-[280px] rounded-2xl border border-border bg-surface p-4 shadow-lg space-y-3">
                   <div className="flex items-center justify-between">
                     <span className="text-[10px] font-bold text-foreground uppercase tracking-wider">Signal Summary</span>
                     <span className="text-[10px] font-bold text-positive uppercase">▲ Bullish</span>
                   </div>
                   <div className="grid grid-cols-2 gap-2">
                     <div className="p-2 rounded-lg bg-elevated/40 border border-border">
                       <p className="text-[8px] text-foreground font-bold uppercase">Conviction</p>
                       <p className="text-[14px] font-bold text-positive font-mono">87%</p>
                     </div>
                     <div className="p-2 rounded-lg bg-elevated/40 border border-border">
                       <p className="text-[8px] text-foreground font-bold uppercase">Fair Value</p>
                       <p className="text-[14px] font-bold text-text-primary font-mono">$204</p>
                     </div>
                     <div className="p-2 rounded-lg bg-elevated/40 border border-border">
                       <p className="text-[8px] text-foreground font-bold uppercase">Risk Level</p>
                       <p className="text-[14px] font-bold text-accent font-mono">Low</p>
                     </div>
                     <div className="p-2 rounded-lg bg-[#2C2A1E] border border-border">
                       <p className="text-[8px] text-[#EDE8DC]/80 font-bold uppercase">Action</p>
                       <p className="text-[14px] font-bold text-positive font-mono">BUY</p>
                     </div>
                   </div>
                   <button 
                     suppressHydrationWarning
                     className="w-full bg-[#2C2A1E] text-[#F5F0E8] text-[10px] font-bold uppercase tracking-wider py-2 rounded-lg hover:bg-[#2C2A1E]/90 transition-all"
                   >
                     Execute Position →
                   </button>
                </div>
             </div>
          </div>
        </div>
      </section>

      {/* SECTION 8 — FAQ ACCORDION */}
      <section id="faq" className="py-24 px-6 lg:px-20 relative">
        <div className="max-w-7xl mx-auto space-y-16">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <h2 className="text-accent text-xs font-black uppercase tracking-[0.3em]">Common Queries</h2>
            <h2 className="text-4xl md:text-5xl font-bold text-foreground tracking-tight">Frequently Asked Questions</h2>
            <p className="text-black font-medium leading-relaxed">
              Everything you need to know about our advanced financial calculation pipeline.
            </p>
          </div>

          <div className="max-w-3xl mx-auto space-y-4">
            {[
              {
                q: "Is this financial advice?",
                a: "No. RAUTREX is a mathematical analysis technology platform offering quant tools, neural forecasting simulations, and risk algorithms. All output data represents mathematical probability metrics, not explicit buying advice."
              },
              {
                q: "How does AI generate signals?",
                a: "We train our signal engine using custom LSTMs (Long Short-Term Memory networks) and gradient boosted trees (XGBoost) alongside automated semantic scraping pipelines measuring real-time institutional sentiment indexes."
              },
              {
                q: "Can beginners use RAUTREX?",
                a: "Yes. Our terminal has pre-configured quant templates and mock portfolio sandboxes that allow retail beginners to understand risk weights without risking real capital."
              },
              {
                q: "Is my portfolio data secure?",
                a: "Absolutely. RAUTREX connects to retail brokerages via read-only APIs that fully encrypt all credentials using bank-grade AES-256 standard protocols. We never hold or request execution capabilities."
              },
              {
                q: "Do I need a Demat account?",
                a: "No, a Demat account is not required. You can utilize RAUTREX purely as a research terminal, inputting manual assets or using mock simulations to build model portfolios."
              }
            ].map((faq, idx) => (
              <div 
                key={idx} 
                className="bg-surface border border-border rounded-[20px] overflow-hidden transition-all duration-300 shadow-sm"
              >
                <button 
                  suppressHydrationWarning
                  onClick={() => setFaqOpenIndex(faqOpenIndex === idx ? null : idx)}
                  className="w-full px-6 py-5 flex items-center justify-between text-left focus:outline-none"
                >
                  <span className="text-sm md:text-base font-bold text-foreground tracking-tight flex items-center gap-3">
                    <HelpCircle size={16} className="text-accent shrink-0" />
                    {faq.q}
                  </span>
                  <motion.span 
                    animate={{ rotate: faqOpenIndex === idx ? 180 : 0 }}
                    transition={{ duration: 0.2 }}
                    className="text-accent"
                  >
                    <ChevronRight size={18} className="transform rotate-90" />
                  </motion.span>
                </button>

                <AnimatePresence initial={false}>
                  {faqOpenIndex === idx && (
                    <motion.div 
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25 }}
                    >
                      <div className="px-6 pb-6 pt-1 text-sm text-secondary font-medium leading-relaxed border-t border-border/40 bg-elevated/10">
                        {faq.a}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </div>

        </div>
      </section>

      {/* SECTION 9 — PRODUCT ROADMAP */}
      <section id="roadmap" className="py-24 px-6 lg:px-20 bg-elevated/10 relative">
        <div className="max-w-7xl mx-auto space-y-16">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <h2 className="text-accent text-xs font-black uppercase tracking-[0.3em]">Future Trajectory</h2>
            <h2 className="text-4xl md:text-5xl font-bold text-foreground tracking-tight">What&apos;s coming next</h2>
            <p className="text-black font-medium leading-relaxed">
              We continuously scale the RAUTREX system. Our engineering roadmap targets full broker integrations and dynamic voice quantitative assistants.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 items-stretch relative max-w-5xl mx-auto">
            
            {/* Timeline cards connected */}
            {[
              { q: "Q2", title: "Portfolio Scanner", desc: "Comprehensive asset scanning mapping real-time correlation risk vectors.", active: true },
              { q: "Q3", title: "AI Copilot", desc: "Natural language compiler processing raw math queries and stress stressor requests.", active: false },
              { q: "Q4", title: "Broker Integration", desc: "Execute target trades straight from Rautrex using read-write bridge APIs.", active: false },
              { q: "Q1", title: "Mobile App", desc: "On-the-go quant alerts, volatility spikes, and ML trend signals direct to your device.", active: false }
            ].map((step, idx) => (
              <motion.div 
                key={idx} 
                whileHover={{ y: -4 }}
                className={cn(
                  "bg-surface border rounded-[24px] p-6 flex flex-col justify-between shadow-sm relative overflow-hidden transition-all duration-300",
                  step.active ? "border-2 border-accent" : "border-border hover:border-accent/40"
                )}
              >
                {step.active && (
                  <div className="absolute top-0 right-0 bg-accent text-[#F5F0E8] text-[8px] font-black uppercase tracking-wider px-2 py-0.5 rounded-bl">
                    ACTIVE
                  </div>
                )}
                
                <div>
                  <div className="w-9 h-9 rounded-lg bg-accent/15 border border-accent/20 flex items-center justify-center font-mono font-black text-accent text-sm mb-5">
                    {step.q}
                  </div>
                  <h3 className="text-base font-bold text-foreground tracking-tight mb-2">{step.title}</h3>
                  <p className="text-xs text-secondary leading-relaxed font-medium">{step.desc}</p>
                </div>
              </motion.div>
            ))}

          </div>
        </div>
      </section>

      {/* FINAL CTA */}
      <section className="py-32 px-6 lg:px-20">
         <div className="max-w-5xl mx-auto rounded-[3rem] bg-gradient-to-br from-accent/20 to-accent/5 border border-accent/10 p-12 md:p-20 text-center relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(circle_at_50%_50%,rgba(0,212,255,0.1),transparent)]" />
            
            <div className="relative z-10 space-y-8">
               <h2 className="text-4xl md:text-6xl font-bold text-foreground tracking-tighter">Ready to trade smarter?</h2>
               <p className="text-xl text-secondary max-w-2xl mx-auto font-medium">
                 Start your quant journey today — no credit card required. 
                 Join the new generation of data-driven retail traders.
               </p>
               
               <div className="flex flex-col items-center gap-4 justify-center">
                 <motion.div

                   whileHover={{ scale: 1.015 }}

                   whileTap={{ scale: 0.97 }}

                 >

                   <Link

                     href="/signup"

                     className="inline-block bg-[#2C2A1E] hover:bg-[#2C2A1E]/95 text-[#F5F0E8] font-black px-12 py-5 rounded-full text-lg transition-all shadow-2xl uppercase tracking-wider"

                   >

                     START ANALYZING FREE — NO CARD REQUIRED

                   </Link>

                 </motion.div>

                 {/* Trust Badges */}
                 <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 mt-2 text-[10px] uppercase font-bold tracking-widest text-accent">
                    <span className="flex items-center gap-1.5"><ShieldAlert size={10} /> Bank-grade security</span>
                    <span className="flex items-center gap-1.5"><PieChart size={10} /> Read-only broker integration</span>
                    <span className="flex items-center gap-1.5"><BrainCircuit size={10} /> Data encrypted</span>
                 </div>
               </div>
            </div>
         </div>
      </section>

    </div>
  );
}
