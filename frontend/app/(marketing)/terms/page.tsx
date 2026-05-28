"use client";

import { Scale, ShieldAlert, Cpu, Landmark } from "lucide-react";
import { motion } from "framer-motion";

export default function TermsPage() {
  return (
    <div className="bg-[var(--bg-primary)] min-h-screen text-[var(--text-primary)] font-sans">
      {/* Header Banner */}
      <section className="bg-[#2C2A1E] text-[#F5F0E8] py-20 px-6 text-center border-b border-border/20">
        <div className="max-w-4xl mx-auto space-y-4">
          <p className="text-accent text-xs font-black uppercase tracking-[0.3em]">Legal Agreements</p>
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-[#F5F0E8]">Terms of Service</h1>
          <p className="text-[#EDE8DC]/80 text-xs md:text-sm max-w-lg mx-auto leading-relaxed">
            Effective Date: May 26, 2026. Please review these structural terms carefully before deploying strategies on the RAUTREX terminal.
          </p>
        </div>
      </section>

      {/* Content */}
      <section className="py-20 px-6 max-w-4xl mx-auto">
        <div className="glass-panel p-8 md:p-12 rounded-[28px] bg-surface border border-border shadow-md space-y-8 text-xs md:text-sm text-text-secondary leading-relaxed">
          
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
              <Scale size={18} className="text-accent" /> 1. Operational License & Agreement
            </h3>
            <p>
              By accessing the RAUTREX quantitative terminal (including our web components, local scripts, and APIs), you consent to be bound by these Terms of Service. If you disagree with any segment of these clauses, you are prohibited from utilizing our tools and services.
            </p>
          </div>

          <div className="space-y-4">
            <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
              <Cpu size={18} className="text-accent" /> 2. API & Network Abuse Boundaries
            </h3>
            <p>
              Users are allocated API access subject to strict computational boundaries and rate limits. High-frequency queries or systemic structural abuse (e.g., executing hundreds of queries per second to strain our neural network or simulation models) is strictly forbidden. 
            </p>
            <p>
              We reserve absolute authority to restrict, suspend, or permanently disable credentials belonging to accounts triggering network safety limits or abusing server resources.
            </p>
          </div>

          <div className="space-y-4">
            <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
              <Landmark size={18} className="text-accent" /> 3. Proprietary Intellectual Property
            </h3>
            <p>
              All software components, visual UI layouts, underlying stochastic differential equations, neural network weights, and programmatic algorithms powering the RAUTREX platform are the exclusive intellectual property of RAUTREX Technologies. Copying, distributing, or reverse-engineering our core models is strictly prohibited without explicit business authorization.
            </p>
          </div>

          <div className="space-y-4">
            <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
              <ShieldAlert size={18} className="text-accent" /> 4. Limitation of Liability
            </h3>
            <p>
              RAUTREX serves exclusively as an analytical research terminal. Under no circumstances shall RAUTREX Technologies, its founders, or developers be liable for direct, indirect, or accidental capital losses incurred by trading real securities based on forecasts, indicators, or Monte Carlo calculations.
            </p>
          </div>

          <div className="pt-6 border-t border-border/40 text-[10px] text-text-muted text-center font-mono">
            RAUTREX LEGAL & PRIVACY OPERATIONS • NEW DELHI, INDIA
          </div>
        </div>
      </section>
    </div>
  );
}
