"use client";

import { useState } from "react";
import { BookOpen, Percent, Brain, Activity, ShieldAlert, ArrowRight } from "lucide-react";
import { motion } from "framer-motion";

export default function DocsPage() {
  const [activeTab, setActiveTab] = useState("monte-carlo");

  const docSections = [
    {
      id: "monte-carlo",
      icon: Activity,
      title: "Monte Carlo Engine",
      subtitle: "Probability Modelling",
      content: (
        <div className="space-y-6">
          <p className="text-text-muted text-sm leading-relaxed">
            Our Monte Carlo simulation engine models prospective portfolio asset distribution using **Geometric Brownian Motion (GBM)**. It projects 10,000 distinct price scenarios across selected intervals to capture the absolute volatility boundary.
          </p>

          <div className="p-5 rounded-2xl bg-[var(--bg-secondary)]/50 border border-border space-y-4">
            <h4 className="font-mono text-xs font-black uppercase text-accent tracking-widest">Stochastic Differential Equation</h4>
            <p className="font-mono text-xs bg-surface border border-border/60 p-3.5 rounded-lg text-foreground text-center">
              dS_t = μ S_t dt + σ S_t dW_t
            </p>
            <p className="text-[11px] text-text-muted leading-relaxed">
              Where <code className="font-mono">μ</code> represents the drift coefficient (expected return), <code className="font-mono">σ</code> is the volatility parameter, and <code className="font-mono">dW_t</code> is the stochastic Wiener process increment modeling randomized market impulses.
            </p>
          </div>

          <div className="space-y-3">
            <h4 className="text-sm font-bold text-foreground uppercase tracking-wider">Metrics Derived</h4>
            <ul className="list-disc pl-5 text-xs text-text-secondary leading-relaxed space-y-2">
              <li><strong>Expected Tail Loss (ETL):</strong> Computes prospective loss at 95% and 99% significance levels.</li>
              <li><strong>Probability of Ruin:</strong> Evaluates target portfolio capital depletion thresholds based on randomized cash flow variances.</li>
              <li><strong>Dynamic Variance Expansion:</strong> Projects asset pricing ranges out to 252 business days (1 calendar trading year).</li>
            </ul>
          </div>
        </div>
      )
    },
    {
      id: "ml-signals",
      icon: Brain,
      title: "ML Signals",
      subtitle: "XGBoost + LSTM Neural Framework",
      content: (
        <div className="space-y-6">
          <p className="text-text-muted text-sm leading-relaxed">
            The machine learning module executes directional classification and regression models daily. By synthesizing historical price feeds, structural indicators, and alternative metrics, it generates a strict directional conviction index.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-4 rounded-xl border border-border bg-surface shadow-sm space-y-2">
              <h5 className="text-xs font-bold text-foreground uppercase tracking-wider">Long Short-Term Memory (LSTM)</h5>
              <p className="text-[11px] text-text-muted leading-relaxed">
                Processes temporal dependencies and multi-step sequence parameters. It excels at recognizing regime shifts and structural patterns spanning months of market data.
              </p>
            </div>
            <div className="p-4 rounded-xl border border-border bg-surface shadow-sm space-y-2">
              <h5 className="text-xs font-bold text-foreground uppercase tracking-wider">XGBoost Decision Trees</h5>
              <p className="text-[11px] text-text-muted leading-relaxed">
                Applies gradient boosting algorithms over discrete statistical parameters (relative strengths, volume ratios, variance spreads) to capture highly robust directional signals.
              </p>
            </div>
          </div>

          <div className="space-y-3">
            <h4 className="text-sm font-bold text-foreground uppercase tracking-wider">Conviction Metrics</h4>
            <p className="text-xs text-text-secondary leading-relaxed">
              Every machine learning prediction is accompanied by a **Conviction Score (0% - 100%)** signifying probability certainty. A conviction score above 80% marks a robust trading signal, while lower metrics recommend holding passive exposure.
            </p>
          </div>
        </div>
      )
    },
    {
      id: "risk-diagnostics",
      icon: ShieldAlert,
      title: "Risk Diagnostics",
      subtitle: "Sharpe, Sortino, & Drawdowns",
      content: (
        <div className="space-y-6">
          <p className="text-text-muted text-sm leading-relaxed">
            The diagnostic core evaluates capital structures against rigorous risk parameters. By linking live broker telemetry, it reports the Sharpe Ratio, Sortino Ratio, and maximum historical drawdown vectors.
          </p>

          <div className="space-y-4">
            <div className="p-4 bg-[var(--bg-secondary)]/50 border border-border rounded-xl flex justify-between items-center gap-4">
              <div>
                <h5 className="text-xs font-bold text-foreground uppercase tracking-wider">Sharpe Ratio</h5>
                <p className="text-[10px] text-text-muted max-w-sm">Evaluates excess portfolio return per unit of absolute deviation.</p>
              </div>
              <span className="font-mono text-xs font-bold text-accent px-3 py-1 bg-surface border border-border rounded">(R_p - R_f) / σ_p</span>
            </div>

            <div className="p-4 bg-[var(--bg-secondary)]/50 border border-border rounded-xl flex justify-between items-center gap-4">
              <div>
                <h5 className="text-xs font-bold text-foreground uppercase tracking-wider">Sortino Ratio</h5>
                <p className="text-[10px] text-text-muted max-w-sm">Differentiates harmful downward volatility from positive upward variances.</p>
              </div>
              <span className="font-mono text-xs font-bold text-accent px-3 py-1 bg-surface border border-border rounded">(R_p - R_f) / σ_d</span>
            </div>
          </div>

          <div className="space-y-3">
            <h4 className="text-sm font-bold text-foreground uppercase tracking-wider">Tail Risk Assessment</h4>
            <p className="text-xs text-text-secondary leading-relaxed">
              The engine automatically calculates portfolio **Value at Risk (VaR)** using historical variance-covariance matrices. This informs the user of potential capital loss parameters over 1-day and 10-day intervals at a 99% confidence level.
            </p>
          </div>
        </div>
      )
    }
  ];

  return (
    <div className="bg-[var(--bg-primary)] min-h-screen text-[var(--text-primary)] font-sans">
      {/* Hero section */}
      <section className="bg-[#2C2A1E] text-[#F5F0E8] py-28 px-6 border-b border-border/20">
        <div className="max-w-4xl mx-auto space-y-6">
          <p className="text-accent text-xs font-black uppercase tracking-[0.3em]">Technical Core</p>
          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-[#F5F0E8]">Platform Documentation</h1>
          <p className="text-[#EDE8DC]/80 text-base md:text-lg max-w-xl leading-relaxed">
            Detailed mathematical explanations, model configurations, and risk algorithms powering the RAUTREX quant terminal.
          </p>
        </div>
      </section>

      {/* Interactive Tabs */}
      <section className="py-24 px-6 max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12">
        {/* Left menu */}
        <div className="lg:col-span-4 space-y-4">
          <div className="space-y-2 mb-6">
            <h2 className="text-accent text-xs font-black uppercase tracking-[0.3em]">Documentation</h2>
            <h2 className="text-2xl font-bold tracking-tight">Core Modules</h2>
          </div>

          <div className="flex flex-col gap-2">
            {docSections.map((sec) => (
              <button 
                suppressHydrationWarning
                key={sec.id}
                onClick={() => setActiveTab(sec.id)}
                className={`w-full p-4 rounded-xl border text-left flex gap-4 items-center transition-all ${
                  activeTab === sec.id 
                    ? "border-accent bg-surface shadow-sm font-bold" 
                    : "border-border/60 bg-surface/50 hover:border-accent/40"
                }`}
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                  activeTab === sec.id ? "bg-accent text-[#F5F0E8]" : "bg-accent/10 text-accent"
                }`}>
                  <sec.icon size={16} />
                </div>
                <div>
                  <p className="text-xs font-bold text-foreground leading-snug">{sec.title}</p>
                  <p className="text-[10px] text-text-muted">{sec.subtitle}</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Right content view */}
        <div className="lg:col-span-8">
          <div className="glass-panel p-8 md:p-10 rounded-[28px] bg-surface border border-border shadow-md min-h-[450px]">
            {docSections.find(s => s.id === activeTab)!.content}
          </div>
        </div>
      </section>
    </div>
  );
}
