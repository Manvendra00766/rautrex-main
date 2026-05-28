"use client";

import { Shield, Eye, Lock, FileKey } from "lucide-react";
import { motion } from "framer-motion";

export default function PrivacyPage() {
  return (
    <div className="bg-[var(--bg-primary)] min-h-screen text-[var(--text-primary)] font-sans">
      {/* Header Banner */}
      <section className="bg-[#2C2A1E] text-[#F5F0E8] py-20 px-6 text-center border-b border-border/20">
        <div className="max-w-4xl mx-auto space-y-4">
          <p className="text-accent text-xs font-black uppercase tracking-[0.3em]">Legal & Compliance</p>
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-[#F5F0E8]">Privacy Policy</h1>
          <p className="text-[#EDE8DC]/80 text-xs md:text-sm max-w-lg mx-auto leading-relaxed">
            Effective Date: May 26, 2026. This policy describes how RAUTREX collects, encrypts, and handles your quantitative and credentials telemetry.
          </p>
        </div>
      </section>

      {/* Content */}
      <section className="py-20 px-6 max-w-4xl mx-auto">
        <div className="glass-panel p-8 md:p-12 rounded-[28px] bg-surface border border-border shadow-md space-y-8 text-xs md:text-sm text-text-secondary leading-relaxed">
          
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
              <Shield size={18} className="text-accent" /> 1. Data Sovereignty & Philosophy
            </h3>
            <p>
              At RAUTREX, we believe that your financial telemetry is exclusively yours. We do not engage in the sale, lease, or distribution of your portfolio telemetry, transaction history, or quantitative credentials to any third-party brokers, market makers, or advertising networks.
            </p>
          </div>

          <div className="space-y-4">
            <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
              <Eye size={18} className="text-accent" /> 2. Information We Collect
            </h3>
            <p>
              To process quantitative simulations and compile diagnostics reports, we collect specific parameters:
            </p>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong>Authentication Credentials:</strong> Names, encrypted email credentials, and basic security parameters.</li>
              <li><strong>Read-Only Broker Connections:</strong> API credentials required to fetch your portfolio holdings. We **never** request or store write-privileges or execution-privileges.</li>
              <li><strong>Telemetry Parameters:</strong> Simulated allocations, stock search tickers, and backtesting logs to analyze algorithm performance metrics.</li>
            </ul>
          </div>

          <div className="space-y-4">
            <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
              <Lock size={18} className="text-accent" /> 3. Data Hardening & Encryption
            </h3>
            <p>
              Your telemetry is encrypted in transit using industry-standard Transport Layer Security (TLS 1.3) and stored at rest using robust **AES-256 encryption systems**. Direct database access is bounded by rigorous multi-factor protocols and network barriers to ensure absolute protection.
            </p>
          </div>

          <div className="space-y-4">
            <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
              <FileKey size={18} className="text-accent" /> 4. GDPR & CCPA Compliance
            </h3>
            <p>
              Under global regulatory standards (including GDPR and CCPA), you reserve full rights over your data. You may request the absolute deletion of your credentials, broker connections, and simulation history at any time. Our database desk will completely purge your data records within 48 hours of submitting a request.
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
