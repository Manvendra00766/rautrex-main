"use client";

import Link from "next/link";
import { ShieldCheck, Users, GraduationCap, ArrowRight } from "lucide-react";
import { motion } from "framer-motion";

export default function AboutPage() {
  return (
    <div className="bg-[var(--bg-primary)] min-h-screen text-[var(--text-primary)] font-sans">
      {/* Hero Banner Section */}
      <section className="bg-[#2C2A1E] text-[#F5F0E8] py-28 px-6 text-center relative overflow-hidden border-b border-border/20">
        <div className="absolute inset-0 bg-radial-gradient from-accent/20 to-transparent pointer-events-none opacity-30" />
        <div className="max-w-4xl mx-auto space-y-6 relative z-10">
          <motion.p 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-accent text-xs font-black uppercase tracking-[0.3em]"
          >
            The Mission
          </motion.p>
          <motion.h1 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-4xl md:text-6xl font-extrabold tracking-tight text-[#F5F0E8]"
          >
            Democratizing Quant Finance
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-[#EDE8DC]/80 text-base md:text-lg max-w-2xl mx-auto leading-relaxed"
          >
            RAUTREX was founded by a team of high-frequency traders and quantitative analysts who wanted to bring institutional-grade analytical power directly to individual retail investors.
          </motion.p>
        </div>
      </section>

      {/* Core Principles */}
      <section className="py-24 px-6 max-w-7xl mx-auto space-y-16">
        <div className="text-center space-y-4">
          <h2 className="text-accent text-xs font-black uppercase tracking-[0.3em]">Core Philosophy</h2>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight">The Principles That Guide Us</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            {
              icon: ShieldCheck,
              title: "Scientific Rigor",
              desc: "No qualitative hype or stock market newsletters. Our entire engine is built on mathematical models, statistical testing, and probability theory."
            },
            {
              icon: Users,
              title: "Absolute Transparency",
              desc: "All backtests disclose exact metrics, Sharpe ratios, and tail risks. We do not hide behind complex math; we explain the exact logic driving every signal."
            },
            {
              icon: GraduationCap,
              title: "Institutional Quality",
              desc: "We bring professional tools—such as Monte Carlo simulations and Black-Scholes options pricing—which usually cost thousands in annual fees, to everyone."
            }
          ].map((item, idx) => (
            <div key={idx} className="glass-panel p-8 rounded-2xl relative overflow-hidden transition-all duration-300 hover:border-accent/30 bg-surface shadow-sm">
              <div className="w-12 h-12 rounded-xl bg-accent/10 flex items-center justify-center text-accent mb-6">
                <item.icon size={24} />
              </div>
              <h3 className="text-xl font-bold text-foreground mb-3">{item.title}</h3>
              <p className="text-text-muted text-sm leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* History and Tech Stack Details */}
      <section className="bg-surface border-y border-border py-24 px-6">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div className="space-y-6">
            <h2 className="text-accent text-xs font-black uppercase tracking-[0.3em]">Behind the Code</h2>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground">Who We Are</h2>
            <p className="text-text-muted leading-relaxed font-medium">
              We are researchers, engineers, and financial developers formerly at major global investment institutions, market makers, and tech giants. Disillusioned by the asymmetry of financial tooling between institutions and retail investors, we assembled in 2024 to build RAUTREX.
            </p>
            <p className="text-text-muted leading-relaxed">
              Our core infrastructure processes millions of real-time ticks daily, generating optimized allocations using modern portfolio theory, advanced neural networks, and historical regression tests.
            </p>
          </div>

          <div className="bg-[var(--bg-secondary)] border border-border p-8 rounded-3xl space-y-6 shadow-sm">
            <h3 className="font-mono text-sm font-black uppercase text-accent tracking-widest">Platform Telemetry</h3>
            <div className="space-y-4">
              {[
                { label: "Data Latency", val: "< 12ms", desc: "Direct market feed synchronization" },
                { label: "Simulations Run", val: "1.2B+", desc: "Monte Carlo scenario analysis computed" },
                { label: "Broker Connections", val: "100%", desc: "Read-only bank-grade API integrations" }
              ].map((stat, i) => (
                <div key={i} className="flex justify-between items-center border-b border-border/40 pb-3 last:border-b-0 last:pb-0">
                  <div>
                    <p className="text-xs font-bold text-foreground uppercase tracking-wider">{stat.label}</p>
                    <p className="text-[11px] text-text-muted">{stat.desc}</p>
                  </div>
                  <p className="font-mono text-xl font-black text-accent">{stat.val}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
