"use client";

import React, { useState, useEffect, useRef } from "react";
import { Info, TrendingUp, Layers, Table, Box, ChevronDown, ChevronUp, Play, Activity, Settings, Download } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { apiFetch } from "@/lib/api";
import { exportOptionsPDF } from "@/lib/exportPDF";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  AreaChart, Area, ScatterChart, Scatter, ZAxis, Legend
} from "recharts";
import { ChartSkeleton } from "@/components/ui/ChartSkeleton";
import { DefaultChart } from "@/components/ui/DefaultChart";
import { ErrorState } from "@/components/ui/ErrorState";
import { TickerChip } from "@/components/ui/TickerChip";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/utils";

import { useMarketStore } from "@/lib/market-store";

export default function OptionsPage() {
  const { activeTicker: ticker, setActiveTicker: setTicker } = useMarketStore();
  const [mode, setMode] = useState("single"); // single, chain, strategy, iv_surface
  const [model, setModel] = useState("black_scholes");
  const [optType, setOptType] = useState("call");
  
  // Single Option Params
  const [S, setS] = useState(150.0);
  const [K, setK] = useState(150.0);
  const [T, setT] = useState(0.5); // years
  const [r, setR] = useState(0.05);
  const [sigma, setSigma] = useState(0.25);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [singleResult, setSingleResult] = useState<any>(null);
  const [greeksCurve, setGreeksCurve] = useState<any[]>([]);
  const [chainResult, setChainResult] = useState<any>(null);
  const [surfaceResult, setSurfaceResult] = useState<any>(null);
  const [strategyResult, setStrategyResult] = useState<any>(null);
  const [configExpanded, setConfigExpanded] = useState(true);
  
  const { toast } = useToast();

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    setConfigExpanded(false);
    
    try {
      if (mode === "single") {
        const data = await apiFetch("/options/price", {
          method: "POST",
          body: JSON.stringify({ model, option_type: optType, S, K, T, r, sigma })
        });
        setSingleResult(data);
        
        // Fetch Greek curves (10 points around S)
        const curvePromises = [];
        const step = (S * 0.4) / 10;
        for (let i = 0; i <= 10; i++) {
          const testS = S * 0.8 + (i * step);
          curvePromises.push(apiFetch("/options/price", {
            method: "POST",
            body: JSON.stringify({ model, option_type: optType, S: testS, K, T, r, sigma })
          }).then(data => ({ S: testS.toFixed(1), ...data.greeks })));
        }
        const curves = await Promise.all(curvePromises);
        setGreeksCurve(curves);
        toast({ type: 'success', title: 'Pricing Calculated', description: `${model.replace('_', ' ')} results ready.` });
      } else if (mode === "chain") {
        const data = await apiFetch(`/options/chain/${ticker}`);
        setChainResult(data);
        toast({ type: 'success', title: 'Chain Loaded', description: `Options chain for ${ticker} retrieved.` });
      } else if (mode === "iv_surface") {
        const data = await apiFetch(`/options/iv-surface/${ticker}`);
        setSurfaceResult(data);
        toast({ type: 'success', title: 'Surface Mapped', description: `IV surface and Greeks grids ready.` });
      } else if (mode === "strategy") {
        const data = await apiFetch("/options/strategy", {
          method: "POST",
          body: JSON.stringify({
            strategy_name: "Long Straddle",
            spot: S,
            legs: [
              { type: "call", strike: S, premium: 5.0, position: 1 },
              { type: "put", strike: S, premium: 5.0, position: 1 }
            ]
          })
        });
        setStrategyResult(data);
        toast({ type: 'success', title: 'Strategy Simulated', description: 'Payoff profile generated.' });
      }
    } catch (err: any) {
      setError(err.message || "Analysis failed");
      toast({ type: 'error', title: 'Error', description: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleExport = () => {
    if (mode === "single" && singleResult) {
      exportOptionsPDF(singleResult, ticker || "Custom");
    } else {
      toast({ type: 'info', title: 'Export', description: 'Exporting chain/surface data...' });
    }
  };

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto w-full pb-12">
      {/* HEADER */}
      <div className="flex justify-between items-center">
         <h1 className="text-2xl font-bold text-white flex items-center gap-2">
           <Layers className="text-accent" /> Derivatives Lab
         </h1>
         <div className="flex items-center gap-2">
            <TickerChip ticker={ticker} onClear={() => setTicker("")} />
            {mode === "single" && singleResult && (
              <Button onClick={handleExport} variant="outline" className="bg-surface border-white/10 gap-2">
                <Download size={16} /> Export PDF
              </Button>
            )}
            <Button onClick={runAnalysis} loading={loading} className="bg-accent hover:bg-accent/90 text-white gap-2 font-bold">
               {loading ? "CALCULATING..." : <><Play size={16} fill="currentColor" /> RUN ANALYSIS</>}
            </Button>
         </div>
      </div>

      {/* TABS */}
      <Tabs value={mode} onValueChange={setMode} className="w-full">
         <TabsList className="bg-surface border border-white/5 p-1 h-12 w-full grid grid-cols-4 rounded-xl">
            <TabsTrigger value="single" className="gap-2 font-bold text-xs uppercase"><Box size={14} /> Single Option</TabsTrigger>
            <TabsTrigger value="chain" className="gap-2 font-bold text-xs uppercase"><Table size={14} /> Options Chain</TabsTrigger>
            <TabsTrigger value="strategy" className="gap-2 font-bold text-xs uppercase"><Layers size={14} /> Strategy Builder</TabsTrigger>
            <TabsTrigger value="iv_surface" className="gap-2 font-bold text-xs uppercase"><Activity size={14} /> IV Surface</TabsTrigger>
         </TabsList>
      </Tabs>

      {/* CONFIG */}
      <div className="glass-panel rounded-2xl overflow-hidden">
         <button 
          onClick={() => setConfigExpanded(!configExpanded)}
          className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors border-b border-white/5"
         >
           <span className="text-sm font-bold text-gray-400 flex items-center gap-2 uppercase tracking-wider">
             <Settings size={16} /> Parameters & Model Selection
           </span>
           {configExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
         </button>
         
         <AnimatePresence>
            {configExpanded && (
               <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden">
                  <div className="p-6 grid grid-cols-1 lg:grid-cols-4 gap-8">
                     <div className="space-y-4">
                        <Label className="text-xs text-gray-500 uppercase font-bold tracking-widest">Model</Label>
                        <div className="space-y-2">
                           {["black_scholes", "binomial", "monte_carlo", "heston"].map(m => (
                             <div key={m} onClick={() => setModel(m)} className={cn("p-2 rounded-lg border text-[10px] font-bold uppercase cursor-pointer transition-all", model === m ? "bg-accent/20 border-accent text-accent" : "bg-surface border-white/5 text-gray-500 hover:border-white/20")}>
                               {m.replace('_', ' ')}
                             </div>
                           ))}
                        </div>
                     </div>

                     <div className="space-y-4 lg:col-span-2 grid grid-cols-3 gap-6">
                        <div className="space-y-2">
                           <Label className="text-[10px] text-gray-500 uppercase font-bold">Spot (S)</Label>
                           <Input type="number" value={S} onChange={e => setS(Number(e.target.value))} className="bg-surface font-mono" />
                        </div>
                        <div className="space-y-2">
                           <Label className="text-[10px] text-gray-500 uppercase font-bold">Strike (K)</Label>
                           <Input type="number" value={K} onChange={e => setK(Number(e.target.value))} className="bg-surface font-mono" />
                        </div>
                        <div className="space-y-2">
                           <Label className="text-[10px] text-gray-500 uppercase font-bold">Time (T, Yrs)</Label>
                           <Input type="number" value={T} onChange={e => setT(Number(e.target.value))} className="bg-surface font-mono" />
                        </div>
                        <div className="space-y-2">
                           <Label className="text-[10px] text-gray-500 uppercase font-bold">Risk-Free (r)</Label>
                           <Input type="number" value={r} onChange={e => setR(Number(e.target.value))} className="bg-surface font-mono" />
                        </div>
                        <div className="space-y-2">
                           <Label className="text-[10px] text-gray-500 uppercase font-bold">Volatility (σ)</Label>
                           <Input type="number" value={sigma} onChange={e => setSigma(Number(e.target.value))} className="bg-surface font-mono" />
                        </div>
                        <div className="space-y-2 flex flex-col justify-end pb-1">
                           <div className="flex bg-surface rounded-lg border border-white/5 p-1 h-10">
                              <button onClick={() => setOptType("call")} className={cn("flex-1 text-[10px] font-bold rounded-md uppercase", optType === 'call' ? "bg-accent text-white" : "text-gray-500")}>Call</button>
                              <button onClick={() => setOptType("put")} className={cn("flex-1 text-[10px] font-bold rounded-md uppercase", optType === 'put' ? "bg-accent text-white" : "text-gray-500")}>Put</button>
                           </div>
                        </div>
                     </div>

                     <div className="space-y-4">
                        <Label className="text-xs text-gray-500 uppercase font-bold tracking-widest">Model Intelligence</Label>
                        <div className="p-3 rounded-xl bg-white/5 border border-white/5 text-[10px] text-gray-400 italic leading-relaxed">
                           {model === 'black_scholes' && "Standard log-normal assumption. Best for European options."}
                           {model === 'binomial' && "50-step Cox-Ross-Rubinstein tree. Handles American exercise features."}
                           {model === 'monte_carlo' && "5,000 path simulation. Handles path-dependent path-dependent dependencies."}
                           {model === 'heston' && "Stochastic volatility model. Captures volatility smiles and skews."}
                        </div>
                     </div>
                  </div>
               </motion.div>
            )}
         </AnimatePresence>
      </div>

      {/* RESULTS */}
      <div className="min-h-[500px]">
        {loading ? (
          <div className="flex flex-col gap-6">
            <div className="grid grid-cols-5 gap-4 h-24">
              {[1,2,3,4,5].map(i => <div key={i} className="glass-panel rounded-2xl animate-pulse bg-white/5" />)}
            </div>
            <ChartSkeleton type="line" className="h-[400px]" />
          </div>
        ) : error ? (
          <ErrorState onRetry={runAnalysis} message={error} />
        ) : mode === "single" && singleResult ? (
          <div className="flex flex-col gap-8">
             <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
                <div className="p-6 rounded-2xl bg-accent/10 border border-accent/20 flex flex-col items-center justify-center">
                   <p className="text-[10px] text-accent font-bold uppercase tracking-widest mb-1">Model Price</p>
                   <p className="text-3xl font-mono font-bold text-white">${singleResult.price.toFixed(2)}</p>
                </div>
                {[
                  { label: "Delta", val: singleResult.greeks.delta, color: "text-blue-400" },
                  { label: "Gamma", val: singleResult.greeks.gamma, color: "text-purple-400" },
                  { label: "Theta", val: singleResult.greeks.theta, color: "text-red-400" },
                  { label: "Vega", val: singleResult.greeks.vega, color: "text-green-400" },
                ].map(g => (
                  <div key={g.label} className="glass-panel p-4 rounded-2xl flex flex-col items-center justify-center">
                    <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">{g.label}</p>
                    <p className={cn("text-xl font-mono font-bold", g.color)}>{g.val.toFixed(4)}</p>
                  </div>
                ))}
             </div>

             <div className="glass-panel p-6 rounded-2xl h-[400px] bg-[#0d0d14]">
                <h3 className="text-sm font-bold uppercase text-gray-500 tracking-wider mb-6 flex items-center gap-2">
                   <Activity size={16} className="text-accent" /> Spot Price Sensitivity (Greeks Curve)
                </h3>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={greeksCurve}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis dataKey="S" stroke="rgba(255,255,255,0.4)" fontSize={10} />
                    <YAxis stroke="rgba(255,255,255,0.4)" fontSize={10} />
                    <Tooltip contentStyle={{ backgroundColor: '#1a1a2e', border: 'none', borderRadius: '12px' }} />
                    <Legend wrapperStyle={{ fontSize: '10px', paddingTop: '20px' }} />
                    <Line type="monotone" dataKey="delta" name="Delta" stroke="#60a5fa" dot={false} strokeWidth={2} />
                    <Line type="monotone" dataKey="gamma" name="Gamma" stroke="#c084fc" dot={false} strokeWidth={2} />
                    <Line type="monotone" dataKey="vega" name="Vega" stroke="#4ade80" dot={false} strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
             </div>
          </div>
        ) : (
          <DefaultChart />
        )}
      </div>
    </div>
  );
}
