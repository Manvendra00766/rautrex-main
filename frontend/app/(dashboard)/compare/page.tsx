"use client";

import { useState } from "react";
import { Play, Activity, TrendingUp, BarChart2, Shield, Crosshair, Award } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from "recharts";
import { ChartSkeleton } from "@/components/ui/ChartSkeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { DefaultChart } from "@/components/ui/DefaultChart";
import { TickerChip } from "@/components/ui/TickerChip";
import { useToast } from "@/components/ui/Toast";
import { useMarketStore } from "@/lib/market-store";

const STRATEGIES = [
  { id: "sma_crossover", name: "SMA Crossover", color: "#00d4ff" },
  { id: "rsi_reversion", name: "RSI Reversion", color: "#ff4d4d" },
  { id: "macd", name: "MACD Strategy", color: "#00ff88" },
  { id: "bollinger", name: "Bollinger Breakout", color: "#ffea00" },
  { id: "momentum", name: "Momentum", color: "#ff00ea" },
];

export default function ComparePage() {
  const { activeTicker: ticker, setActiveTicker: setTicker } = useMarketStore();
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const runComparison = async () => {
    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const data = await apiFetch("/compare/strategies", {
        method: "POST",
        body: JSON.stringify({
          ticker,
          start_date: startDate,
          end_date: endDate,
          strategies: STRATEGIES.map(s => ({ name: s.name, type: s.id, params: {} })),
          initial_capital: 10000
        })
      });
      
      setResults(data);
      toast({ type: 'success', title: 'Comparison Complete', description: `Successfully analyzed strategies for ${ticker}.` });
    } catch (err: any) {
      setError(err.message || "Failed to run comparison");
      toast({ type: 'error', title: 'Comparison Failed', description: err.message });
    } finally {
      setLoading(false);
    }
  };

  const getRadarData = (metrics: any) => {
    if (!metrics) return [];
    const strats = Object.keys(metrics);
    
    // Normalize metrics for radar (0 to 100)
    // We'll compare: Return, Sharpe, Sortino, Win Rate, Profit Factor
    const rawData = {
      Return: {}, Sharpe: {}, Sortino: {}, WinRate: {}, ProfitFactor: {}
    };
    
    let maxReturn = -Infinity, maxSharpe = -Infinity, maxSortino = -Infinity, maxWinRate = -Infinity, maxPF = -Infinity;
    
    strats.forEach(s => {
      const m = metrics[s];
      rawData.Return[s] = m.total_return || 0;
      rawData.Sharpe[s] = m.sharpe_ratio || 0;
      rawData.Sortino[s] = m.sortino_ratio || 0;
      rawData.WinRate[s] = m.win_rate || 0;
      rawData.ProfitFactor[s] = (m.profit_factor !== undefined && m.profit_factor !== Infinity) ? m.profit_factor : 0; // Cap PF for radar
      
      maxReturn = Math.max(maxReturn, rawData.Return[s]);
      maxSharpe = Math.max(maxSharpe, rawData.Sharpe[s]);
      maxSortino = Math.max(maxSortino, rawData.Sortino[s]);
      maxWinRate = Math.max(maxWinRate, rawData.WinRate[s]);
      maxPF = Math.max(maxPF, rawData.ProfitFactor[s]);
    });

    const normalize = (val: number, max: number) => max > 0 ? (val / max) * 100 : 0;

    return [
      { subject: 'Return', ...Object.fromEntries(strats.map(s => [s, normalize(rawData.Return[s], maxReturn)])) },
      { subject: 'Sharpe', ...Object.fromEntries(strats.map(s => [s, normalize(rawData.Sharpe[s], maxSharpe)])) },
      { subject: 'Sortino', ...Object.fromEntries(strats.map(s => [s, normalize(rawData.Sortino[s], maxSortino)])) },
      { subject: 'Win Rate', ...Object.fromEntries(strats.map(s => [s, normalize(rawData.WinRate[s], maxWinRate)])) },
      { subject: 'Profit F.', ...Object.fromEntries(strats.map(s => [s, normalize(rawData.ProfitFactor[s], maxPF)])) },
    ];
  };

  const stratColors: Record<string, string> = {
    "Buy & Hold": "#7c3aed",
    "SMA Crossover": "#00d4ff",
    "RSI Reversion": "#ff4d4d",
    "MACD Strategy": "#00ff88",
    "Bollinger Breakout": "#ffea00",
    "Momentum": "#ff00ea"
  };

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto w-full pb-12">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-white">Strategy Comparison</h1>
          <TickerChip ticker={ticker} onClear={() => setTicker("")} />
        </div>
        <Button 
          onClick={runComparison} 
          loading={loading}
          className="bg-accent hover:bg-accent/90 text-white gap-2 px-6"
        >
          {loading ? "COMPARING..." : <><Play size={16} fill="currentColor" /> RUN COMPARISON</>}
        </Button>
      </div>

      <div className="glass-panel p-4 rounded-2xl flex items-center gap-6 mb-4">
        <div className="space-y-2 flex-1">
          <Label className="text-gray-400 text-xs uppercase font-bold">Start Date</Label>
          <Input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="bg-surface border-white/5" />
        </div>
        <div className="space-y-2 flex-1">
          <Label className="text-gray-400 text-xs uppercase font-bold">End Date</Label>
          <Input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="bg-surface border-white/5" />
        </div>
        <div className="flex-2 flex items-center gap-4 pt-6">
          <span className="text-xs text-gray-500 italic">Comparing 5 Base Strategies + Buy & Hold</span>
        </div>
      </div>

      {loading ? (
        <ChartSkeleton type="line" />
      ) : error ? (
        <ErrorState type="error" onRetry={runComparison} message={error} />
      ) : results ? (
        <div className="flex flex-col gap-6">
          {/* Winner Badges */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            {Object.entries(results.winners).map(([metric, strat]: any) => (
              <div key={metric} className="p-3 bg-surface border border-white/5 rounded-xl flex flex-col items-center justify-center text-center gap-1 relative overflow-hidden group">
                <div className="absolute inset-0 bg-accent/5 translate-y-full group-hover:translate-y-0 transition-transform" />
                <Award size={16} className="text-accent mb-1" />
                <span className="text-[10px] text-gray-500 uppercase tracking-wider">{metric.replace('_', ' ')}</span>
                <span className="text-xs font-bold text-white max-w-full truncate">{strat}</span>
              </div>
            ))}
          </div>

          {/* Equity Curves */}
          <div className="glass-panel p-6 rounded-2xl h-[500px] bg-[#0d0d14]">
            <h3 className="font-semibold text-lg mb-6 flex items-center gap-2">
              <TrendingUp size={18} className="text-accent" /> Combined Equity Curves
            </h3>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={results.chart_data} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                <XAxis dataKey="time" stroke="rgba(255,255,255,0.5)" fontSize={10} minTickGap={50} />
                <YAxis stroke="rgba(255,255,255,0.5)" fontSize={10} tickFormatter={(v) => `$${(v/1000).toFixed(0)}k`} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                  itemStyle={{ fontSize: '12px' }}
                  labelStyle={{ color: '#888', marginBottom: '8px' }}
                />
                <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '20px' }} />
                {Object.keys(stratColors).map(strat => (
                   results.metrics[strat] && (
                     <Line 
                       key={strat} 
                       type="monotone" 
                       dataKey={strat} 
                       name={strat} 
                       stroke={stratColors[strat]} 
                       strokeWidth={strat === "Buy & Hold" ? 2 : 1.5} 
                       strokeDasharray={strat === "Buy & Hold" ? "5 5" : ""} 
                       dot={false} 
                     />
                   )
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Comparison Table */}
            <div className="lg:col-span-2 glass-panel rounded-2xl overflow-hidden flex flex-col">
              <div className="p-6 border-b border-white/5">
                <h3 className="font-semibold text-lg flex items-center gap-2"><BarChart2 size={18} className="text-accent" /> Metrics Comparison</h3>
              </div>
              <div className="flex-1 overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-[10px] text-gray-500 uppercase bg-surface/50">
                    <tr>
                      <th className="px-4 py-3">Strategy</th>
                      <th className="px-4 py-3 text-right">Total Ret</th>
                      <th className="px-4 py-3 text-right">CAGR</th>
                      <th className="px-4 py-3 text-right">Sharpe</th>
                      <th className="px-4 py-3 text-right">Max DD</th>
                      <th className="px-4 py-3 text-right">Win Rate</th>
                      <th className="px-4 py-3 text-right">PF</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(results.metrics).map(([stratName, m]: any) => (
                      <tr key={stratName} className="border-b border-white/5 hover:bg-white/5 font-mono text-xs">
                        <td className="px-4 py-3 font-bold" style={{ color: stratColors[stratName] || '#fff' }}>{stratName}</td>
                        <td className={`px-4 py-3 text-right ${results.winners.total_return === stratName ? 'text-[#00d4ff] font-bold' : ''}`}>
                          {((m.total_return || 0) * 100).toFixed(2)}%
                        </td>
                        <td className={`px-4 py-3 text-right ${results.winners.cagr === stratName ? 'text-[#00d4ff] font-bold' : ''}`}>
                          {((m.cagr || 0) * 100).toFixed(2)}%
                        </td>
                        <td className={`px-4 py-3 text-right ${results.winners.sharpe_ratio === stratName ? 'text-[#00d4ff] font-bold' : ''}`}>
                          {(m.sharpe_ratio || 0).toFixed(2)}
                        </td>
                        <td className={`px-4 py-3 text-right ${results.winners.max_drawdown === stratName ? 'text-[#00d4ff] font-bold' : ''}`}>
                          {((m.max_drawdown || 0) * 100).toFixed(2)}%
                        </td>
                        <td className={`px-4 py-3 text-right ${results.winners.win_rate === stratName ? 'text-[#00d4ff] font-bold' : ''}`}>
                          {((m.win_rate || 0) * 100).toFixed(1)}%
                        </td>
                        <td className={`px-4 py-3 text-right ${results.winners.profit_factor === stratName ? 'text-[#00d4ff] font-bold' : ''}`}>
                          {(m.profit_factor !== undefined && m.profit_factor !== Infinity) ? m.profit_factor.toFixed(2) : (m.profit_factor === Infinity ? '∞' : '0.00')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Radar Chart */}
            <div className="glass-panel p-6 rounded-2xl h-[400px]">
              <h3 className="font-semibold text-lg mb-4 flex items-center gap-2"><Crosshair size={18} className="text-accent" /> Strategy Profiles</h3>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={getRadarData(results.metrics)}>
                  <PolarGrid stroke="rgba(255,255,255,0.1)" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: '#888', fontSize: 10 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                    itemStyle={{ fontSize: '10px' }}
                  />
                  {Object.keys(stratColors).map(strat => (
                     results.metrics[strat] && (
                       <Radar 
                         key={strat} 
                         name={strat} 
                         dataKey={strat} 
                         stroke={stratColors[strat]} 
                         fill={stratColors[strat]} 
                         fillOpacity={0.1} 
                       />
                     )
                  ))}
                  <Legend wrapperStyle={{ fontSize: '10px' }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      ) : (
        <DefaultChart />
      )}
    </div>
  );
}
