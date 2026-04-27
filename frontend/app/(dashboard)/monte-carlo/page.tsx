"use client";

import { useState, useRef, useEffect } from "react";
import { Play, Download, AlertCircle, ChevronDown, ChevronUp, BarChart2, Plus, Info, Activity } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { apiFetch } from "@/lib/api";
import { exportMonteCarloPDF } from "@/lib/exportPDF";
import MetricCard from "@/components/metric-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Line, BarChart, Bar, Cell, Legend } from "recharts";
import { ChartSkeleton } from "@/components/ui/ChartSkeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { DefaultChart } from "@/components/ui/DefaultChart";
import { TickerChip } from "@/components/ui/TickerChip";
import { useToast } from "@/components/ui/Toast";

import { useMarketStore } from "@/lib/market-store";

export default function MonteCarloPage() {
  const { activeTicker: ticker, setActiveTicker: setTicker } = useMarketStore();
  const [horizon, setHorizon] = useState("365");
  const [sims, setSims] = useState([2000]);
  const [investment, setInvestment] = useState(10000);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [configExpanded, setConfigExpanded] = useState(true);
  const { toast } = useToast();

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    setResults(null);
    setConfigExpanded(false);
    
    try {
      const data = await apiFetch("/monte-carlo/run", {
        method: "POST",
        body: JSON.stringify({
          ticker,
          time_horizon: parseInt(horizon),
          num_simulations: sims[0],
          initial_investment: investment
        })
      });
      setResults(data);
      toast({ type: 'success', title: 'Simulation Complete', description: `${sims[0]} paths generated for ${ticker}.` });
    } catch (err: any) {
      setError(err.message || "Simulation failed");
      toast({ type: 'error', title: 'Error', description: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleExport = () => {
    if (!results) return;
    exportMonteCarloPDF(results, ticker);
  };

  // Prepare chart data
  const chartData = results ? results.percentiles.p50.map((_: any, i: number) => {
    const date = new Date();
    date.setDate(date.getDate() + i);
    return {
      time: date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
      p5: results.percentiles.p5[i],
      p25: results.percentiles.p25[i],
      p50: results.percentiles.p50[i],
      p75: results.percentiles.p75[i],
      p95: results.percentiles.p95[i],
    };
  }) : [];

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto w-full pb-12">
      {/* TOP */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <BarChart2 className="text-accent" /> Risk Projection
          </h1>
          <TickerChip ticker={ticker} onClear={() => setTicker("")} />
        </div>
        <div className="flex items-center gap-2">
          {results && (
            <Button onClick={handleExport} variant="outline" className="bg-surface border-white/10 gap-2">
              <Download size={16} /> Export PDF
            </Button>
          )}
           <Button 
            onClick={runSimulation} 
            loading={loading}
            className="bg-accent hover:bg-accent/90 text-white gap-2 px-6"
          >
            {loading ? `RUNNING ${sims[0]} SIMS...` : <><Play size={16} fill="currentColor" /> EXECUTE PROJECTION</>}
          </Button>
        </div>
      </div>

      {/* CONFIG */}
      <div className="glass-panel rounded-2xl overflow-hidden">
        <button 
          onClick={() => setConfigExpanded(!configExpanded)}
          className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors border-b border-white/5"
        >
          <span className="text-sm font-bold text-gray-400 flex items-center gap-2 uppercase tracking-wider">
            <Info size={16} /> Projection Parameters
          </span>
          {configExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
        <AnimatePresence>
          {configExpanded && (
            <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden">
              <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-10">
                <div className="space-y-4">
                  <div className="flex justify-between items-end">
                    <Label className="text-xs text-gray-500 uppercase font-bold">Path Sample Size</Label>
                    <span className="text-accent font-mono text-sm font-bold">{sims[0].toLocaleString()}</span>
                  </div>
                  <Slider value={sims} onValueChange={setSims} max={10000} min={100} step={100} className="py-4" />
                  <p className="text-[10px] text-gray-500 italic">Higher samples increase accuracy but require more compute time (~3s per 5k paths).</p>
                </div>

                <div className="space-y-4">
                   <Label className="text-xs text-gray-500 uppercase font-bold">Projection Horizon</Label>
                   <Tabs value={horizon} onValueChange={setHorizon} className="w-full">
                    <TabsList className="grid grid-cols-5 bg-surface border border-white/5 h-10">
                      {["30", "90", "180", "365", "730"].map(h => (
                        <TabsTrigger key={h} value={h} className="text-xs font-bold">{h}D</TabsTrigger>
                      ))}
                    </TabsList>
                  </Tabs>
                  <p className="text-[10px] text-gray-500 italic">Trading days to project into the future using GBM (Geometric Brownian Motion).</p>
                </div>

                <div className="space-y-4">
                  <Label className="text-xs text-gray-500 uppercase font-bold">Capital Commitment</Label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-accent font-bold font-mono">$</span>
                    <Input type="number" value={investment} onChange={e => setInvestment(Number(e.target.value))} className="pl-8 bg-surface border-white/5 font-mono text-lg" />
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* MAIN */}
      <div className="min-h-[600px] flex flex-col gap-6">
        {loading ? (
          <div className="flex flex-col gap-6">
             <div className="grid grid-cols-4 gap-4 h-32">
                {[1,2,3,4].map(i => <div key={i} className="glass-panel rounded-2xl animate-pulse bg-white/5" />)}
             </div>
             <ChartSkeleton type="line" className="h-[500px]" />
          </div>
        ) : error ? (
          <ErrorState onRetry={runSimulation} message={error} />
        ) : results ? (
          <div className="flex flex-col gap-6">
            {/* KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard 
                  title="Expected Value" 
                  value={`$${(results.expected_value || 0).toLocaleString(undefined, {maximumFractionDigits: 0})}`} 
                  icon={null} 
                  trend={`${(((results.expected_value || investment)/investment - 1)*100).toFixed(1)}% Return`}
                />
                <MetricCard 
                  title="Value at Risk (95%)" 
                  value={`$${(results.var || 0).toLocaleString(undefined, {maximumFractionDigits: 0})}`} 
                  icon={null} 
                  trend="Max Probable Loss"
                />
                <MetricCard 
                  title="Prob. of Profit" 
                  value={`${(results.prob_profit || 0).toFixed(1)}%`} 
                  icon={null} 
                  trend="Likelihood of Upside"
                />
                <MetricCard 
                  title="Annual Volatility" 
                  value={`${((results.volatility || 0) * 100).toFixed(1)}%`} 
                  icon={null} 
                  trend="Historical Std Dev"
                />
            </div>

            {/* Main Area Chart */}
            <div className="glass-panel p-6 rounded-2xl h-[500px] bg-[#0d0d14] relative overflow-hidden">
               <div className="flex justify-between items-center mb-6 relative z-10">
                 <h3 className="font-semibold text-lg flex items-center gap-2"><Activity size={18} className="text-accent" /> Probabilistic Outcomes</h3>
                 <div className="flex gap-4">
                    <div className="flex items-center gap-2">
                       <div className="w-3 h-3 rounded-full bg-accent" />
                       <span className="text-[10px] text-gray-500 font-bold">MEDIAN (P50)</span>
                    </div>
                    <div className="flex items-center gap-2">
                       <div className="w-3 h-3 rounded-full bg-purple-500/30" />
                       <span className="text-[10px] text-gray-500 font-bold">CONFIDENCE BANDS</span>
                    </div>
                 </div>
               </div>

               <div className="h-[380px] w-full relative z-10">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
                       <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                       <XAxis dataKey="time" stroke="rgba(255,255,255,0.5)" fontSize={10} minTickGap={100} />
                       <YAxis domain={['auto', 'auto']} stroke="rgba(255,255,255,0.5)" fontSize={10} tickFormatter={(v) => `$${(v/1000).toFixed(0)}k`} />
                       <Tooltip 
                        contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                        itemStyle={{ fontSize: '11px', fontWeight: 'bold' }}
                        labelStyle={{ color: '#888', marginBottom: '8px' }}
                       />
                       {/* Percentile Bands */}
                       <Area type="monotone" dataKey="p95" stroke="none" fill="#7c3aed" fillOpacity={0.05} />
                       <Area type="monotone" dataKey="p75" stroke="none" fill="#7c3aed" fillOpacity={0.1} />
                       <Area type="monotone" dataKey="p25" stroke="none" fill="#7c3aed" fillOpacity={0.1} />
                       <Area type="monotone" dataKey="p5" stroke="none" fill="#7c3aed" fillOpacity={0.05} />
                       {/* Median Path */}
                       <Line type="monotone" dataKey="p50" name="Median Price" stroke="#00d4ff" strokeWidth={3} dot={false} activeDot={{ r: 6, fill: '#fff', stroke: '#00d4ff', strokeWidth: 2 }} />
                    </AreaChart>
                  </ResponsiveContainer>
               </div>
            </div>

            {/* Bottom Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
               <div className="glass-panel p-6 rounded-2xl bg-[#0d0d14]">
                  <h3 className="font-semibold text-sm uppercase text-gray-500 tracking-wider mb-6">Return Distribution</h3>
                  <div className="h-[250px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={results.histogram}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                        <XAxis dataKey="bin" stroke="rgba(255,255,255,0.5)" fontSize={10} tickFormatter={(v) => `$${(v/1000).toFixed(1)}k`} />
                        <YAxis hide />
                        <Tooltip cursor={{fill: 'transparent'}} contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }} />
                        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                           {results.histogram.map((entry: any, index: number) => (
                             <Cell key={index} fill={entry.bin > investment ? "rgba(0, 212, 255, 0.4)" : "rgba(239, 68, 68, 0.4)"} />
                           ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
               </div>

               <div className="glass-panel p-6 rounded-2xl flex flex-col justify-center gap-6 bg-[#0d0d14]">
                  <h3 className="font-bold flex items-center gap-2"><Info size={16} className="text-accent" /> Simulation Intelligence</h3>
                  <div className="space-y-4">
                     <p className="text-xs text-gray-400 leading-relaxed">
                        Based on {sims[0]} simulated price paths, the expected portfolio value at the end of {horizon} days is <span className="text-white font-bold">${results.expected_value.toLocaleString()}</span>. 
                     </p>
                     <div className="p-4 rounded-xl bg-accent/5 border border-accent/10">
                        <p className="text-xs text-accent font-bold mb-1 uppercase tracking-widest">Risk Summary</p>
                        <p className="text-xs text-gray-400">There is a <span className="text-white font-bold">{results.prob_profit.toFixed(1)}%</span> probability that the asset will trade above your initial investment of ${investment.toLocaleString()}.</p>
                     </div>
                  </div>
               </div>
            </div>
          </div>
        ) : (
          <DefaultChart />
        )}
      </div>
    </div>
  );
}
