"use client";

import { MessageSquare, MessageCircle, Calendar, Users, Trophy } from "lucide-react";
import { motion } from "framer-motion";

const Github = (props: React.SVGProps<SVGSVGElement>) => (
  <svg
    viewBox="0 0 24 24"
    width="24"
    height="24"
    stroke="currentColor"
    strokeWidth="2"
    fill="none"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
    <path d="M9 18c-4.51 2-5-2-7-2" />
  </svg>
);

export default function CommunityPage() {
  const socialCards = [
    {
      icon: MessageCircle,
      title: "Discord Server",
      desc: "Join 15,000+ active quantitative developers, retail algorithmic traders, and data scientists. Discuss strategy parameters, ML signals, and coding configurations in real-time.",
      action: "Connect on Discord",
      stats: "15,248 members"
    },
    {
      icon: Github,
      title: "Open Source Libraries",
      desc: "We maintain and contribute to multiple open-source quantitative backtesting repositories in Rust and Python. Review our mathematical frameworks, submit PRs, or fork repositories.",
      action: "Explore Repositories",
      stats: "3.2k stars"
    },
    {
      icon: MessageSquare,
      title: "Developer Forums",
      desc: "A structural forum dedicated to deeper discussions regarding systemic Sharpe optimization, portfolio asset correlations, machine learning hyperparameters, and backtesting regression bugs.",
      action: "Browse Discussions",
      stats: "240 active topics"
    }
  ];

  return (
    <div className="bg-[var(--bg-primary)] min-h-screen text-[var(--text-primary)] font-sans">
      {/* Hero Header */}
      <section className="bg-[#2C2A1E] text-[#F5F0E8] py-28 px-6 text-center border-b border-border/20">
        <div className="max-w-4xl mx-auto space-y-6">
          <motion.p 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-accent text-xs font-black uppercase tracking-[0.3em]"
          >
            Quant Network
          </motion.p>
          <motion.h1 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-4xl md:text-6xl font-extrabold tracking-tight text-[#F5F0E8]"
          >
            Connect With the Quant Collective
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-[#EDE8DC]/80 text-base md:text-lg max-w-xl mx-auto leading-relaxed"
          >
            Join a global community of modern quantitative developers, algorithmic engineers, and rigorous systematic traders sharing strategies and code.
          </motion.p>
        </div>
      </section>

      {/* Main Grid */}
      <section className="py-24 px-6 max-w-7xl mx-auto space-y-16">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {socialCards.map((card, idx) => (
            <div key={idx} className="glass-panel p-8 rounded-2xl bg-surface border border-border/60 shadow-sm flex flex-col justify-between transition-all duration-300 hover:border-accent/30 min-h-[320px]">
              <div className="space-y-6">
                <div className="flex justify-between items-center">
                  <div className="w-12 h-12 rounded-xl bg-accent/10 flex items-center justify-center text-accent">
                    <card.icon size={24} />
                  </div>
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-text-muted">
                    {card.stats}
                  </span>
                </div>
                <div className="space-y-2">
                  <h3 className="text-xl font-bold text-foreground">{card.title}</h3>
                  <p className="text-text-muted text-xs leading-relaxed">{card.desc}</p>
                </div>
              </div>

              <div className="pt-6">
                <button 
                  suppressHydrationWarning
                  className="w-full bg-[#2C2A1E] hover:bg-[#2C2A1E]/95 text-[#F5F0E8] font-bold uppercase tracking-wider text-[10px] py-3 rounded-lg shadow-sm transition-all"
                >
                  {card.action}
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Community Events */}
      <section className="bg-surface border-y border-border py-24 px-6">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div className="space-y-6">
            <h2 className="text-accent text-xs font-black uppercase tracking-[0.3em]">Developer Gatherings</h2>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground">Global Hackathons & Seminars</h2>
            <p className="text-text-muted text-sm leading-relaxed">
              We sponsor quarterly virtual quant hackathons where developers assemble to build predictive indicators, optimization models, or custom broker connectors using the RAUTREX system.
            </p>
            <div className="space-y-4 pt-2">
              <div className="flex gap-4 items-center">
                <Calendar size={18} className="text-accent shrink-0" />
                <span className="text-xs text-text-secondary font-medium">Next Quant Hackathon: September 15, 2026</span>
              </div>
              <div className="flex gap-4 items-center">
                <Trophy size={18} className="text-accent shrink-0" />
                <span className="text-xs text-text-secondary font-medium">Grand Prize Allocation: $25,000 Trading Capital Credit</span>
              </div>
            </div>
          </div>

          <div className="bg-[var(--bg-secondary)]/50 border border-border p-8 rounded-3xl space-y-6 shadow-sm">
            <h3 className="font-mono text-xs font-black uppercase text-accent tracking-widest">Community Spotlight</h3>
            <div className="space-y-4">
              {[
                { author: "HFT_Dev_99", repo: "rautrex-rust-client", desc: "Low-latency asynchronous rust bindings for market sockets." },
                { author: "QuantSteph", repo: "lstm-hyperopt", desc: "Automated hyperparameter tuner for the LSTM directional core." },
                { author: "BrokerBridge", repo: "ibkr-read-connector", desc: "Interactive Brokers portfolio read-only connector bridge." }
              ].map((spot, i) => (
                <div key={i} className="bg-surface border border-border/40 p-4 rounded-2xl flex flex-col gap-1 shadow-sm">
                  <div className="flex justify-between items-center">
                    <span className="font-mono text-xs font-bold text-foreground">{spot.repo}</span>
                    <span className="text-[9px] font-bold text-accent uppercase tracking-wider">{spot.author}</span>
                  </div>
                  <p className="text-[10px] text-text-muted leading-relaxed">{spot.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
