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

const FeatureCard = ({ icon: Icon, title, desc }: { icon: any, title: string, desc: string }) => (
  <motion.div 
    whileHover={{ y: -5 }}
    className="glass-panel p-8 rounded-2xl group relative overflow-hidden transition-all hover:border-accent/30"
  >
    <div className="absolute top-0 left-0 w-1 h-0 bg-accent group-hover:h-full transition-all duration-300" />
    <div className="w-12 h-12 rounded-xl bg-accent/10 flex items-center justify-center text-accent mb-6 group-hover:scale-110 transition-transform">
      <Icon size={24} />
    </div>
    <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
    <p className="text-gray-500 text-sm leading-relaxed mb-6">{desc}</p>
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
      <section className="relative min-h-screen flex items-center pt-20 px-6 lg:px-20 overflow-hidden">
        {/* Background Gradients */}
        <div className="absolute top-[-10%] right-[-10%] w-[50%] h-[50%] bg-accent/10 rounded-full blur-[120px] animate-cyan-pulse" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[30%] h-[30%] bg-purple-500/10 rounded-full blur-[100px]" />

        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-13 gap-12 items-center z-10">
          {/* Left Content */}
          <div className="lg:col-span-8 flex flex-col gap-8">
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/10 border border-accent/20 w-fit"
            >
              <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
              <span className="text-[10px] font-black uppercase tracking-widest text-accent">Quant Finance Platform</span>
            </motion.div>
            
            <motion.h1 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="text-5xl md:text-7xl font-bold text-white leading-[1.1] tracking-tighter"
            >
              Your personal hedge fund <br /> 
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent to-accent-secondary">operating system</span>
            </motion.h1>

            <motion.p 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-lg md:text-xl text-gray-400 max-w-2xl leading-relaxed"
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
                <Button className="bg-accent hover:bg-accent/90 text-black font-black px-8 py-7 rounded-full text-lg cyan-glow transition-all hover:scale-105 active:scale-95">
                  GET STARTED FREE
                </Button>
              </Link>
              <Button variant="outline" className="border-white/10 text-white font-bold px-8 py-7 rounded-full text-lg hover:bg-white/5">
                VIEW DEMO
              </Button>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="flex items-center gap-6 pt-8"
            >
              <div className="flex -space-x-3">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="w-10 h-10 rounded-full border-2 border-background bg-surface flex items-center justify-center text-[10px] font-bold text-gray-400 overflow-hidden">
                    <img src={`https://i.pravatar.cc/150?u=${i}`} alt="user" />
                  </div>
                ))}
              </div>
              <p className="text-sm text-gray-500 font-medium">
                <span className="text-white font-bold">Trusted by 1,000+</span> quantitative traders
              </p>
            </motion.div>
          </div>

          {/* Right Dashboard Preview */}
          <motion.div 
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.5, duration: 0.8 }}
            className="lg:col-span-5 relative hidden lg:block"
          >
            <div className="relative z-10 rounded-3xl border border-white/10 bg-[#0d0d14] p-4 shadow-2xl animate-float">
               {/* Mock Dashboard UI */}
               <div className="w-full aspect-square rounded-2xl bg-surface/50 overflow-hidden flex flex-col">
                  <div className="h-12 border-b border-white/5 flex items-center px-4 gap-2">
                     <div className="w-3 h-3 rounded-full bg-red-500/50" />
                     <div className="w-3 h-3 rounded-full bg-amber-500/50" />
                     <div className="w-3 h-3 rounded-full bg-green-500/50" />
                  </div>
                  <div className="flex-1 p-6 space-y-6">
                     <div className="h-32 w-full rounded-xl bg-accent/5 border border-accent/10 flex items-end p-4 gap-2">
                        {[40, 70, 45, 90, 65, 80, 50, 85].map((h, i) => (
                          <div key={i} className="flex-1 bg-accent/20 rounded-t-sm" style={{ height: `${h}%` }} />
                        ))}
                     </div>
                     <div className="grid grid-cols-2 gap-4">
                        <div className="h-20 rounded-xl bg-white/5 border border-white/5" />
                        <div className="h-20 rounded-xl bg-white/5 border border-white/5" />
                     </div>
                     <div className="space-y-2">
                        <div className="h-3 w-3/4 bg-white/5 rounded-full" />
                        <div className="h-3 w-1/2 bg-white/5 rounded-full" />
                     </div>
                  </div>
               </div>

               {/* Floating Cards */}
               <motion.div 
                animate={{ y: [0, -10, 0] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                className="absolute -top-6 -left-12 glass-panel p-4 rounded-2xl border-accent/20 cyan-glow"
               >
                  <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">Portfolio Return</p>
                  <p className="text-xl font-black text-accent">+24.3%</p>
               </motion.div>

               <motion.div 
                animate={{ y: [0, 10, 0] }}
                transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
                className="absolute top-1/2 -right-8 glass-panel p-4 rounded-2xl border-purple-500/20"
               >
                  <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">Sharpe Ratio</p>
                  <p className="text-xl font-black text-purple-400">1.87</p>
               </motion.div>

               <motion.div 
                animate={{ x: [0, -10, 0] }}
                transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
                className="absolute -bottom-8 left-12 glass-panel p-4 rounded-2xl border-white/10"
               >
                  <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">VaR (95%)</p>
                  <p className="text-xl font-black text-white">2.1%</p>
               </motion.div>
            </div>
            
            {/* Ambient Light */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-accent/20 rounded-full blur-[100px] -z-10" />
          </motion.div>
        </div>
      </section>

      {/* STATS SECTION */}
      <section className="bg-surface border-y border-white/5 py-12">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8">
          {[
            { label: "Global Tickers", value: "50,000", suffix: "+" },
            { label: "Quant Models", value: "10", suffix: "+" },
            { label: "Data Quality", value: "Real-time", isText: true },
            { label: "Pricing", value: "100", suffix: "% Free" }
          ].map((stat, i) => (
            <div key={i} className="text-center space-y-1">
              <p className="text-3xl md:text-4xl font-black text-white">
                {stat.isText ? stat.value : <AnimatedCounter value={stat.value} suffix={stat.suffix} />}
              </p>
              <p className="text-[10px] md:text-xs font-bold text-gray-500 uppercase tracking-[0.2em]">{stat.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FEATURES SECTION */}
      <section id="features" className="py-32 px-6 lg:px-20 relative">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-3xl mx-auto mb-20 space-y-4">
            <h2 className="text-accent text-xs font-black uppercase tracking-[0.3em]">Institutional Grade</h2>
            <h2 className="text-4xl md:text-5xl font-bold text-white tracking-tight">Powerful modules for every edge</h2>
            <p className="text-gray-500 leading-relaxed">
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
      <section id="how-it-works" className="py-32 px-6 lg:px-20 bg-surface/30">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-20">
             <h2 className="text-4xl font-bold text-white">Simple three-step workflow</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-12 relative">
             {/* Connection Arrows (Desktop) */}
             <div className="hidden md:block absolute top-1/2 left-1/3 -translate-x-1/2 -translate-y-1/2 text-accent/20">
                <ArrowRight size={48} />
             </div>
             <div className="hidden md:block absolute top-1/2 left-2/3 -translate-x-1/2 -translate-y-1/2 text-accent/20">
                <ArrowRight size={48} />
             </div>

             {[
               { icon: Search, title: "Search any stock", desc: "Access 50,000+ global tickers with deep fundamentals and real-time data." },
               { icon: BrainCircuit, title: "Run analysis", desc: "Select your modules. Run simulations, train models, or optimize weights." },
               { icon: MousePointer2, title: "Make decisions", desc: "Execute trades with institutional conviction and managed risk parameters." }
             ].map((step, i) => (
               <div key={i} className="flex flex-col items-center text-center space-y-6">
                  <div className="w-20 h-20 rounded-3xl bg-background border border-white/5 flex items-center justify-center text-accent cyan-glow">
                    <step.icon size={32} />
                  </div>
                  <div className="space-y-2">
                    <h4 className="text-xl font-bold text-white">{step.title}</h4>
                    <p className="text-gray-500 text-sm leading-relaxed max-w-xs">{step.desc}</p>
                  </div>
               </div>
             ))}
          </div>
        </div>
      </section>

      {/* FINAL CTA */}
      <section className="py-32 px-6 lg:px-20">
         <div className="max-w-5xl mx-auto rounded-[3rem] bg-gradient-to-br from-accent/20 to-purple-500/10 border border-white/10 p-12 md:p-20 text-center relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(circle_at_50%_50%,rgba(0,212,255,0.1),transparent)]" />
            
            <div className="relative z-10 space-y-8">
               <h2 className="text-4xl md:text-6xl font-bold text-white tracking-tighter">Ready to trade smarter?</h2>
               <p className="text-xl text-gray-400 max-w-2xl mx-auto">
                 Start your quant journey today — no credit card required. 
                 Join the new generation of data-driven retail traders.
               </p>
               <Link href="/signup">
                <Button className="bg-white hover:bg-gray-200 text-black font-black px-12 py-8 rounded-full text-xl transition-all hover:scale-105 active:scale-95 shadow-2xl">
                    CREATE FREE ACCOUNT
                </Button>
               </Link>
            </div>
         </div>
      </section>
    </div>
  );
}
