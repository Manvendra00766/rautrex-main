"use client";

import React, { useState } from "react";
import { useSandbox } from "@/lib/sandboxContext";
import { X } from "lucide-react";

export function SandboxBanner() {
  const { isSandbox, exitSandbox } = useSandbox();
  const [isVisible, setIsVisible] = useState(true);

  if (!isSandbox || !isVisible) return null;

  return (
    <div className="w-full bg-[#EDE8DC] border-b border-[#D4CEC4] text-[#1A1714] py-2.5 px-4 md:px-6 flex flex-col md:flex-row items-center justify-between gap-3 text-xs font-medium z-[1000] relative">
      <div className="flex items-center gap-2.5">
        <span className="bg-[#8B6F47] text-[#FAF7F2] px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider select-none shrink-0">
          SANDBOX
        </span>
        <span className="text-left font-sans text-xs">
          You're exploring in Sandbox Mode — all data is simulated. No real trades or portfolio required.
        </span>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <button
          onClick={() => {
            alert("Tour started! Rautrex sandbox lets you preview quantitative trading models without funding an account. Click any link in the grouped sidebar on your left to explore AI Signals, DCF Valuations, Monte Carlo simulations, and live portfolios!");
          }}
          className="text-[#8B6F47] hover:underline flex items-center gap-1 font-bold uppercase tracking-wider text-xs"
        >
          Take the tour →
        </button>
        <button
          onClick={exitSandbox}
          className="bg-[#8B6F47] hover:bg-[#8B6F47]/90 text-[#FAF7F2] px-3 py-1.5 rounded-[4px] font-bold uppercase tracking-widest text-xs transition-all hover:scale-[1.02] active:scale-[0.98] border-none"
        >
          Exit Sandbox
        </button>
        <button
          onClick={() => setIsVisible(false)}
          className="text-[#8C8278] hover:text-[#1A1714] transition-colors p-1"
          aria-label="Dismiss banner"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
}
