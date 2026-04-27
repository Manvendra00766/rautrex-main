"use client";

import React, { useState, useRef } from "react";
import { Play, Download, TrendingUp, BarChart2, Activity, Settings, Calendar, ChevronDown, ChevronUp } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { apiFetch } from "@/lib/api";
import MetricCard from "@/components/metric-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ComposedChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Line, Legend } from "recharts";
import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";
import { ChartSkeleton } from "@/components/ui/ChartSkeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { DefaultChart } from "@/components/ui/DefaultChart";
import { TickerChip } from "@/components/ui/TickerChip";
import { useToast } from "@/components/ui/Toast";

const STRATEGIES = [
  { id: "sma_crossover", name: "SMA Crossover", desc: "Trend following via dual moving averages", icon: <TrendingUp size={24} /> },
  { id: "rsi_reversion", name: "RSI Mean Reversion", desc: "Fade extremes using RSI oscillator", icon: <Activity size={24} /> },
  { id: "macd", name: "MACD Strategy", desc: "Momentum indicator crossing signal line", icon: <BarChart2 size={24} /> },
  { id: "bollinger", name: "Bollinger Breakout", desc: "Volatility bands expansion/contraction", icon: <Settings size={24} /> },
  { id: "momentum", name: "Time-Series Momentum", desc: "Buy recent winners, sell losers", icon: <TrendingUp size={24} /> },
];

import { useMarketStore } from "@/lib/market-store";

import { exportBacktestPDF } from "@/lib/exportPDF";

export default function BacktestPage() {
  const { activeTicker: ticker, setActiveTicker: setTicker } = useMarketStore();
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [strategy, setStrategy] = useState("sma_crossover");
  const [capital, setCapital] = useState(10000);
  const [commission, setCommission] = useState(0.1);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [configExpanded, setConfigExpanded] = useState(true);
  const { toast } = useToast();

  // Strategy Parameters State
  const [smaFast, setSmaFast] = useState(50);
  const [smaSlow, setSmaSlow] = useState(200);
  const [rsiPeriod, setRsiPeriod] = useState(14);
  const [rsiOversold, setRsiOversold] = useState(30);
  const [rsiOverbought, setRsiOverbought] = useState(70);

  const reportRef = useRef<HTMLDivElement>(null);

  const runBacktest = async () => {
    setLoading(true);
    setError(null);
    setResults(null);
    setConfigExpanded(false);

    try {
      let params = {};
      if (strategy === "sma_crossover") params = { fast_period: smaFast, slow_period: smaSlow };
      else if (strategy === "rsi_reversion") params = { rsi_period: rsiPeriod, oversold: rsiOversold, overbought: rsiOverbought };
      
      const data = await apiFetch("/backtest/run", {
        method: "POST",
        body: JSON.stringify({
          ticker,
          start_date: startDate,
          end_date: endDate,
          strategy_type: strategy,
          strategy_params: params,
          initial_capital: capital,
          commission: commission
        })
      });
      
      setResults(data);
      toast({ type: 'success', title: 'Backtest Complete', description: `Analysis for ${ticker} finished successfully.` });
    } catch (err: any) {
      setError(err.message || "Failed to run backtest");
      toast({ type: 'error', title: 'Backtest Failed', description: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleExportPDF = () => {
    if (!results) return;
    exportBacktestPDF(results, ticker, strategy);
  };

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto w-full pb-12">
      {/* TOP: Page title & actions */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-white">Strategy Backtester</h1>
          <TickerChip ticker={ticker} onClear={() => setTicker("")} />
        </div>
        <div className="flex items-center gap-2">
          {results && (
            <Button onClick={handleExportPDF} variant="outline" className="bg-surface border-white/10 gap-2">
              <Download size={16} /> Export PDF
            </Button>
          )}
          <Button 
            onClick={runBacktest} 
            loading={loading}
            className="bg-accent hover:bg-accent/90 text-white gap-2 px-6"
          >
            {loading ? "SIMULATING..." : <><Play size={16} fill="currentColor" /> RUN ANALYSIS</>}
          </Button>
        </div>
      </div>

      {/* BELOW: Configuration panel */}
      <div className="glass-panel rounded-2xl overflow-hidden">
        <button 
          onClick={() => setConfigExpanded(!configExpanded)}
          className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors border-b border-white/5"
        >
          <span className="text-sm font-bold text-gray-400 flex items-center gap-2 uppercase tracking-wider">
            <Settings size={16} /> Strategy & Parameters
          </span>
          {configExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
        
        <AnimatePresence>
          {configExpanded && (
            <motion.div 
              initial={{ height: 0 }}
              animate={{ height: "auto" }}
              exit={{ height: 0 }}
              className="overflow-hidden"
            >
              <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="space-y-4">
                  <Label className="text-xs text-gray-500 uppercase font-bold">Strategy Engine</Label>
                  <div className="grid grid-cols-1 gap-2">
                    {STRATEGIES.map(s => (
                      <div 
                        key={s.id}
                        onClick={() => setStrategy(s.id)}
                        className={`p-3 rounded-xl border cursor-pointer transition-all flex items-center gap-3 ${strategy === s.id ? "bg-accent/10 border-accent" : "bg-surface border-white/5 hover:border-white/20"}`}
                      >
                        <div className={`p-2 rounded-lg ${strategy === s.id ? "bg-accent/20 text-accent" : "bg-white/5 text-gray-400"}`}>
                          {React.cloneElement(s.icon as React.ReactElement, { size: 18 })}
                        </div>
                        <span className={`text-sm font-bold ${strategy === s.id ? "text-white" : "text-gray-400"}`}>{s.name}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-4">
                  <Label className="text-xs text-gray-500 uppercase font-bold">Timeframe & Capital</Label>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label className="text-gray-400 text-xs">Start Date</Label>
                      <Input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="bg-surface border-white/5" />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-gray-400 text-xs">End Date</Label>
                      <Input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="bg-surface border-white/5" />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-gray-400 text-xs">Capital ($)</Label>
                      <Input type="number" value={capital} onChange={e => setCapital(Number(e.target.value))} className="bg-surface border-white/5" />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-gray-400 text-xs">Fee (%)</Label>
                      <Input type="number" step="0.01" value={commission} onChange={e => setCommission(Number(e.target.value))} className="bg-surface border-white/5" />
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <Label className="text-xs text-gray-500 uppercase font-bold">Parameters</Label>
                  <div className="bg-surface/50 rounded-xl p-4 border border-white/5">
                    {strategy === "sma_crossover" && (
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label className="text-gray-400 text-xs">Fast</Label>
                          <Input type="number" value={smaFast} onChange={e => setSmaFast(Number(e.target.value))} className="bg-surface border-white/5" />
                        </div>
                        <div className="space-y-2">
                          <Label className="text-gray-400 text-xs">Slow</Label>
                          <Input type="number" value={smaSlow} onChange={e => setSmaSlow(Number(e.target.value))} className="bg-surface border-white/5" />
                        </div>
                      </div>
                    )}
                    {strategy === "rsi_reversion" && (
                      <div className="grid grid-cols-3 gap-2">
                        <div className="space-y-2">
                          <Label className="text-gray-400 text-xs">Period</Label>
                          <Input type="number" value={rsiPeriod} onChange={e => setRsiPeriod(Number(e.target.value))} className="bg-surface border-white/5 px-2" />
                        </div>
                        <div className="space-y-2">
                          <Label className="text-gray-400 text-xs">OS</Label>
                          <Input type="number" value={rsiOversold} onChange={e => setRsiOversold(Number(e.target.value))} className="bg-surface border-white/5 px-2" />
                        </div>
                        <div className="space-y-2">
                          <Label className="text-gray-400 text-xs">OB</Label>
                          <Input type="number" value={rsiOverbought} onChange={e => setRsiOverbought(Number(e.target.value))} className="bg-surface border-white/5 px-2" />
                        </div>
                      </div>
                    )}
                    {["macd", "bollinger", "momentum"].includes(strategy) && (
                      <p className="text-xs text-gray-500 italic">Default optimized parameters will be used.</p>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* MAIN: Results area */}
      <div className="min-h-[600px] flex flex-col gap-6">
        {loading ? (
          <div className="flex flex-col gap-6">
             <div className="grid grid-cols-4 gap-4 h-32">
                {[1,2,3,4].map(i => <div key={i} className="glass-panel rounded-2xl animate-pulse bg-white/5" />)}
             </div>
             <div className="h-[500px]">
               <ChartSkeleton type="line" />
             </div>
          </div>
        ) : error ? (
          <ErrorState type="error" onRetry={runBacktest} message={error} />
        ) : results ? (
          <div className="flex flex-col gap-6" ref={reportRef}>
            {/* 4 Metric Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
             <MetricCard 
               title="Total Return" 
               value={`${((results.metrics.strategy?.total_return || 0) * 100).toFixed(2)}%`} 
               trend={`BnH: ${((results.metrics.benchmark?.total_return || 0) * 100).toFixed(2)}%`} 
               valueClassName="text-green-400"
             />
             <MetricCard 
               title="CAGR" 
               value={`${((results.metrics.strategy?.cagr || 0) * 100).toFixed(2)}%`} 
               trend={`BnH: ${((results.metrics.benchmark?.cagr || 0) * 100).toFixed(2)}%`} 
               valueClassName="text-accent"
             />
             <MetricCard 
               title="Max Drawdown" 
               value={`${((results.metrics.strategy?.max_drawdown || 0) * 100).toFixed(2)}%`} 
               trend={`BnH: ${((results.metrics.benchmark?.max_drawdown || 0) * 100).toFixed(2)}%`} 
               valueClassName="text-red-400"
             />
             <MetricCard 
               title="Sharpe Ratio" 
               value={(results.metrics.strategy?.sharpe_ratio || 0).toFixed(2)} 
               trend={`BnH: ${(results.metrics.benchmark?.sharpe_ratio || 0).toFixed(2)}`} 
               valueClassName="text-white"
             />
            </div>

            {/* Main Chart */}
            <div className="glass-panel p-6 rounded-2xl h-[500px] bg-[#0d0d14]">
              <h3 className="font-semibold text-lg mb-6 flex items-center gap-2">
                <Activity size={18} className="text-accent" /> Equity Curve & Drawdown
              </h3>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={results.chart_data} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ff4d4d" stopOpacity={0.15}/>
                      <stop offset="95%" stopColor="#ff4d4d" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                  <XAxis dataKey="time" stroke="rgba(255,255,255,0.5)" fontSize={10} minTickGap={50} />
                  <YAxis yAxisId="left" stroke="rgba(255,255,255,0.5)" fontSize={10} tickFormatter={(v) => `$${(v/1000).toFixed(0)}k`} />
                  <YAxis yAxisId="right" orientation="right" stroke="#ff4d4d" fontSize={10} tickFormatter={(v) => `${(v*100).toFixed(0)}%`} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                    itemStyle={{ fontSize: '12px' }}
                    labelStyle={{ color: '#888', marginBottom: '8px' }}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '20px' }} />
                  <Line yAxisId="left" type="monotone" dataKey="equity" name="Strategy Equity" stroke="#00d4ff" strokeWidth={2} dot={false} activeDot={{ r: 6, fill: '#fff', stroke: '#00d4ff', strokeWidth: 2 }} />
                  <Line yAxisId="left" type="monotone" dataKey="bnh_equity" name="Buy & Hold" stroke="#7c3aed" strokeWidth={2} strokeDasharray="5 5" dot={false} />
                  <Area yAxisId="right" type="monotone" dataKey="drawdown" name="Drawdown" fill="url(#drawdownGradient)" stroke="#ff4d4d" strokeWidth={1} fillOpacity={1} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            {/* Secondary Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pb-12">
               {/* Trade Log */}
               <div className="glass-panel rounded-2xl overflow-hidden flex flex-col h-[400px]">
                <div className="p-6 border-b border-white/5">
                  <h3 className="font-semibold text-lg">Detailed Trade Log</h3>
                </div>
                <div className="flex-1 overflow-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="text-[10px] text-gray-500 uppercase bg-surface/50 sticky top-0 backdrop-blur-md">
                      <tr>
                        <th className="px-6 py-3">Entry</th>
                        <th className="px-6 py-3">Exit</th>
                        <th className="px-6 py-3 text-right">Return</th>
                        <th className="px-6 py-3 text-right">PnL</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(results.trades || []).map((t: any, i: number) => (
                        <tr key={i} className="border-b border-white/5 hover:bg-white/5 font-mono">                          <td className="px-6 py-3 text-xs">{t.entry_date}</td>
                          <td className="px-6 py-3 text-xs">{t.exit_date}</td>
                          <td className={`px-6 py-3 text-right text-xs font-bold ${t.return_pct > 0 ? 'text-green-500' : 'text-red-500'}`}>
                            {(t.return_pct * 100).toFixed(2)}%
                          </td>
                          <td className={`px-6 py-3 text-right text-xs ${t.net_pnl > 0 ? 'text-green-500' : 'text-red-500'}`}>
                            ${t.net_pnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Advanced Metrics */}
              <div className="glass-panel p-6 rounded-2xl space-y-4">
                <h3 className="font-semibold text-lg">Advanced Performance Metrics</h3>
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { label: "Profit Factor", value: (results.metrics.strategy?.profit_factor || 0).toFixed(2) },
                    { label: "Win Rate", value: ((results.metrics.strategy?.win_rate || 0) * 100).toFixed(1) + "%" },
                    { label: "Avg Win", value: ((results.metrics.strategy?.avg_win || 0) * 100).toFixed(2) + "%" },
                    { label: "Avg Loss", value: ((results.metrics.strategy?.avg_loss || 0) * 100).toFixed(2) + "%" },
                    { label: "Total Trades", value: results.metrics.strategy?.total_trades || 0 },
                    { label: "Volatility", value: ((results.metrics.strategy?.annualized_volatility || 0) * 100).toFixed(2) + "%" },
                  ].map(m => (
                    <div key={m.label} className="p-4 rounded-xl bg-surface border border-white/5 flex justify-between items-center">
                      <span className="text-xs text-gray-500 uppercase font-bold tracking-wider">{m.label}</span>
                      <span className="text-sm font-mono font-bold text-white">{m.value}</span>
                    </div>
                  ))}
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
