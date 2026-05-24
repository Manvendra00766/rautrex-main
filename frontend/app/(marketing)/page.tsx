"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
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
  ArrowRight
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

const FeatureCard = ({ icon: Icon, title, desc, badge }: { icon: any, title: string, desc: string, badge?: string }) => (
  <motion.div 
    whileHover={{ y: -5 }}
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
    <button className="text-accent text-xs font-bold uppercase tracking-widest flex items-center gap-2 group-hover:gap-3 transition-all">
      Explore <ChevronRight size={14} />
    </button>
  </motion.div>
);

// --- Page ---

export default function HomePage() {
  return (
    <div className="flex flex-col w-full">
      {/* HERO SECTION */}
      <section className="relative min-h-screen flex items-center pt-12 px-6 lg:px-20 overflow-hidden bg-background">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-13 gap-12 items-center z-10">
          {/* Left Content */}
          <div className="lg:col-span-8 flex flex-col gap-8">
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-[4px] bg-elevated/50 border border-border w-fit"
            >
              <div className="w-[6px] h-[6px] rounded-full bg-accent" />
              <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-accent">Quant Finance Platform</span>
            </motion.div>
            
            <motion.h1 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="text-[58px] font-bold text-foreground leading-[1.1] tracking-tighter"
            >
              Your personal hedge fund <br /> 
              <span className="text-accent">operating system</span>
            </motion.h1>

            <motion.p 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-[18px] text-secondary max-w-[560px] leading-[1.6]"
            >
              Institutional-grade tools for retail traders. Monte Carlo simulation, ML signals, 
              options pricing, portfolio optimization — all in one platform.
            </motion.p>

            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="flex flex-wrap gap-4 pt-4"
            >
              <Link href="/signup">
                <button className="bg-[#2C2A1E] hover:bg-[#2C2A1E]/90 text-[#F5F0E8] font-bold px-[28px] py-[14px] rounded-[6px] text-[13px] uppercase tracking-wider transition-all active:scale-95 shadow-md">
                  RUN YOUR FIRST SIMULATION FREE
                </button>
              </Link>
              <button className="bg-transparent border border-border text-foreground font-bold px-[28px] py-[14px] rounded-[6px] text-[13px] uppercase tracking-wider hover:bg-elevated/50 transition-all active:scale-95">
                VIEW DEMO
              </button>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-8"
            >
              <div className="glass-panel p-4 rounded-xl border border-border bg-surface shadow-sm hover:border-accent/30 transition-all flex flex-col justify-between space-y-3">
                <div className="flex gap-0.5 text-accent text-xs">
                  {"★★★★★"}
                </div>
                <p className="text-[12px] text-text-primary leading-relaxed font-medium italic">
                  "Rautrex has completely changed my strategy validation. Running 10k Monte Carlo simulations in seconds right in the browser is unprecedented."
                </p>
                <div>
                  <h5 className="text-[11px] font-bold text-text-primary">Sarah Jenkins</h5>
                  <p className="text-[10px] text-text-muted">Quant Researcher, AlphaVanguard Fund</p>
                </div>
              </div>

              <div className="glass-panel p-4 rounded-xl border border-border bg-surface shadow-sm hover:border-accent/30 transition-all flex flex-col justify-between space-y-3">
                <div className="flex gap-0.5 text-accent text-xs">
                  {"★★★★★"}
                </div>
                <p className="text-[12px] text-text-primary leading-relaxed font-medium italic">
                  "The ML Signal Engine's ensemble conviction (LSTM + XGBoost) provides the most reliable statistical foundation for my daily trades."
                </p>
                <div>
                  <h5 className="text-[11px] font-bold text-text-primary">Marcus Thorne</h5>
                  <p className="text-[10px] text-text-muted">Independent Systematic Trader</p>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Right Dashboard Preview */}
          <motion.div 
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.5, duration: 0.8 }}
            className="lg:col-span-5 relative hidden lg:block"
          >
            <div className="relative z-10 rounded-3xl border border-border bg-[#F5F0E8] p-4 shadow-2xl animate-float">
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
                animate={{ y: [0, -8, 0] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                className="absolute -top-6 -left-12 glass-panel p-3.5 rounded-xl border border-accent/30 shadow-md bg-surface"
               >
                  <p className="text-[8px] text-text-muted font-bold uppercase mb-0.5 tracking-wider">Portfolio Return</p>
                  <p className="text-md font-bold tracking-tight text-text-primary font-mono">+24.3%</p>
               </motion.div>

               <motion.div 
                animate={{ y: [0, 8, 0] }}
                transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
                className="absolute top-1/3 -right-8 glass-panel p-3.5 rounded-xl border border-accent/30 shadow-md bg-surface"
               >
                  <p className="text-[8px] text-text-muted font-bold uppercase mb-0.5 tracking-wider">Sharpe Ratio</p>
                  <p className="text-md font-bold tracking-tight text-accent font-mono">1.87</p>
               </motion.div>

               <motion.div 
                animate={{ x: [0, -8, 0] }}
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
              <p className="text-3xl md:text-4xl font-black text-foreground">
                {stat.isText ? stat.value : <AnimatedCounter value={stat.value} suffix={stat.suffix} />}
              </p>
              <p className="text-[10px] md:text-xs font-bold text-muted uppercase tracking-[0.2em]">{stat.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FEATURES SECTION */}
      <section id="features" className="py-32 px-6 lg:px-20 relative">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-3xl mx-auto mb-20 space-y-4">
            <h2 className="text-accent text-xs font-black uppercase tracking-[0.3em]">Institutional Grade</h2>
            <h2 className="text-4xl md:text-5xl font-bold text-foreground tracking-tight">Powerful modules for every edge</h2>
            <p className="text-muted leading-relaxed font-medium">
              We've consolidated professional tools that usually cost thousands of dollars into a single, seamless experience.
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
                  <button className="w-full bg-[#2C2A1E] text-[#F5F0E8] text-[10px] font-bold uppercase tracking-wider py-2 rounded-lg hover:bg-[#2C2A1E]/90 transition-all">
                    Execute Position →
                  </button>
                </div>
             </div>
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
               <Link href="/signup">
                <Button className="bg-foreground hover:bg-foreground/90 text-background font-black px-12 py-8 rounded-full text-xl transition-all hover:scale-105 active:scale-95 shadow-2xl">
                    START ANALYZING FREE — NO CARD REQUIRED
                </Button>
               </Link>
            </div>
         </div>
      </section>
    </div>
  );
}
