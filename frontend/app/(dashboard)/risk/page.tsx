"use client";

import { useState, useEffect } from "react";
import { ShieldAlert, Activity, AlertTriangle, TrendingDown, ChevronDown, ChevronUp, Play, Plus, X, Info, Download } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { apiFetch } from "@/lib/api";
import { exportRiskPDF } from "@/lib/exportPDF";
import MetricCard from "@/components/metric-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import { ChartSkeleton } from "@/components/ui/ChartSkeleton";
import { DefaultChart } from "@/components/ui/DefaultChart";
import { ErrorState } from "@/components/ui/ErrorState";
import { useToast } from "@/components/ui/Toast";
import { usePortfolioOverview } from "@/lib/use-portfolio-overview";
import { cn } from "@/lib/utils";

export default function RiskPage() {
  const { overview } = usePortfolioOverview();
  const [portfolio, setPortfolio] = useState<{ ticker: string; weight: number }[]>([]);
  const [newTicker, setNewTicker] = useState("");
  const [newWeight, setNewWeight] = useState("");
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<any>(null);
  const [stressResults, setStressResults] = useState<any>(null);
  const [factors, setFactors] = useState<any>(null);
  const [scenarios, setScenarios] = useState<any>(null);
  const [configExpanded, setConfigExpanded] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    if (!overview?.positions?.length) return;
    setPortfolio(
      overview.positions.map((position) => ({
        ticker: position.ticker,
        weight: position.weight_pct / 100,
      }))
    );
  }, [overview]);

  const totalWeight = portfolio.reduce((sum, item) => sum + item.weight, 0);

  const addAsset = () => {
    if (!newTicker || !newWeight) return;
    setPortfolio([...portfolio, { ticker: newTicker.toUpperCase(), weight: Number(newWeight) }]);
    setNewTicker("");
    setNewWeight("");
  };

  const removeAsset = (index: number) => {
    setPortfolio(portfolio.filter((_, i) => i !== index));
  };

  const runRiskAnalysis = async () => {
    if (Math.abs(totalWeight - 1.0) > 0.001) {
      toast({ type: 'warning', title: 'Invalid Weights', description: 'Total portfolio weight must sum to 100%.' });
      return;
    }
    
    setLoading(true);
    setError(null);
    setConfigExpanded(false);
    
    try {
      const [pData, sData, fData, scData] = await Promise.all([
        apiFetch("/risk/portfolio", { method: "POST", body: JSON.stringify({ portfolio, start_date: startDate, end_date: endDate, benchmark: "^GSPC" }) }),
        apiFetch("/risk/stress-test", { method: "POST", body: JSON.stringify({ portfolio, start_date: startDate, end_date: endDate }) }),
        apiFetch("/risk/factors", { method: "POST", body: JSON.stringify({ portfolio, start_date: startDate }) }),
        apiFetch("/risk/scenarios", { method: "POST", body: JSON.stringify({ portfolio }) })
      ]);
      
      setResults(pData);
      setStressResults(sData);
      setFactors(fData);
      setScenarios(scData);
      
      toast({ type: 'success', title: 'Analysis Complete', description: 'Risk metrics and stress tests generated.' });
    } catch (err: any) {
      setError(err.message || "Failed to run risk analysis");
      toast({ type: 'error', title: 'Error', description: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleExport = () => {
    if (!results) return;
    const portfolioLabel = portfolio.map(p => p.ticker).join(", ");
    exportRiskPDF(results, portfolioLabel);
  };

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto w-full pb-12">
      {/* TOP HEADER */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <ShieldAlert className="text-red-500" /> Portfolio Risk Audit
          </h1>
          {overview?.portfolio && (
            <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-bold mt-1">
              {overview.portfolio.name}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {results && (
            <Button onClick={handleExport} variant="outline" className="bg-surface border-white/10 gap-2">
              <Download size={16} /> Export Audit PDF
            </Button>
          )}
          <Button 
            onClick={runRiskAnalysis} 
            loading={loading}
            className="bg-accent hover:bg-accent/90 text-white gap-2 px-6 font-bold"
          >
            {loading ? "AUDITING..." : <><Play size={16} fill="currentColor" /> RUN RISK AUDIT</>}
          </Button>
        </div>
      </div>

      {/* CONFIGURATION */}
      <div className="glass-panel rounded-2xl overflow-hidden">
        <button 
          onClick={() => setConfigExpanded(!configExpanded)}
          className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors border-b border-white/5"
        >
          <span className="text-sm font-bold text-gray-400 flex items-center gap-2 uppercase tracking-wider">
            <Info size={16} /> Portfolio Composition & Scope
          </span>
          {configExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
        
        <AnimatePresence>
          {configExpanded && (
            <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden">
              <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-12">
                <div className="space-y-6">
                  <div className="flex justify-between items-center">
                    <Label className="text-xs text-gray-500 uppercase font-bold tracking-widest">Asset Allocation</Label>
                    <span className={cn("text-[10px] font-bold px-2 py-0.5 rounded-full", totalWeight > 1.0 ? "bg-red-500/20 text-red-500" : "bg-accent/20 text-accent")}>
                      TOTAL: {(totalWeight * 100).toFixed(1)}%
                    </span>
                  </div>
                  
                  <div className="space-y-2 max-h-[250px] overflow-auto pr-2 custom-scrollbar">
                    {portfolio.map((item, idx) => (
                      <div key={idx} className="flex items-center gap-3 p-3 rounded-xl bg-surface border border-white/5">
                        <div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center font-bold text-xs">{item.ticker}</div>
                        <div className="flex-1">
                          <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                            <div className="h-full bg-accent" style={{ width: `${item.weight * 100}%` }} />
                          </div>
                        </div>
                        <div className="w-16 text-right font-mono text-xs font-bold text-white">{(item.weight * 100).toFixed(1)}%</div>
                        <button onClick={() => removeAsset(idx)} className="p-1 hover:text-red-500 text-gray-600 transition-colors"><X size={14} /></button>
                      </div>
                    ))}
                  </div>

                  <div className="grid grid-cols-5 gap-2 pt-2 border-t border-white/5">
                     <Input placeholder="Ticker" value={newTicker} onChange={e => setNewTicker(e.target.value)} className="col-span-2 bg-surface h-9 text-xs" />
                     <Input placeholder="Weight (e.g. 0.2)" type="number" value={newWeight} onChange={e => setNewWeight(e.target.value)} className="col-span-2 bg-surface h-9 text-xs" />
                     <Button onClick={addAsset} variant="outline" className="h-9 border-accent/30 text-accent"><Plus size={16} /></Button>
                  </div>
                </div>

                <div className="space-y-6">
                   <Label className="text-xs text-gray-500 uppercase font-bold tracking-widest">Temporal scope</Label>
                   <div className="grid grid-cols-2 gap-4">
                     <div className="space-y-2">
                       <p className="text-[10px] text-gray-500 font-bold uppercase">Backfill Start</p>
                       <Input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="bg-surface h-10" />
                     </div>
                     <div className="space-y-2">
                       <p className="text-[10px] text-gray-500 font-bold uppercase">End Date</p>
                       <Input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="bg-surface h-10" />
                     </div>
                   </div>
                   <div className="p-4 rounded-xl bg-white/5 border border-white/5">
                     <h4 className="text-[10px] font-bold text-gray-400 uppercase mb-2">Methodology Note</h4>
                     <p className="text-[10px] text-gray-500 leading-relaxed italic">
                        Risk metrics are calculated from the live transaction-backed portfolio, annualized on a 252-day basis, benchmarked to SPY, with a 95% historical VaR estimate.
                     </p>
                   </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* RESULTS MAIN */}
      <div className="min-h-[600px] flex flex-col gap-6">
        {loading ? (
          <div className="flex flex-col gap-8">
             <div className="grid grid-cols-4 gap-4 h-32">
                {[1,2,3,4].map(i => <div key={i} className="glass-panel rounded-2xl animate-pulse bg-white/5" />)}
             </div>
             <ChartSkeleton type="line" className="h-[400px]" />
          </div>
        ) : error ? (
          <ErrorState onRetry={runRiskAnalysis} message={error} />
        ) : results ? (
          <div className="flex flex-col gap-8">
             {/* ROW 1: Metrics */}
             <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard 
                  title="Risk Score" 
                  value={(results.risk_score || 0).toFixed(1)} 
                  icon={<AlertTriangle className={cn((results.risk_score || 0) > 70 ? "text-red-500" : "text-green-500")} />} 
                  trend="Aggregate Risk (0-100)"
                  valueClassName={cn((results.risk_score || 0) > 70 ? "text-red-500" : "text-green-500")}
                />
                <MetricCard 
                  title="Max Drawdown" 
                  value={`${((results.metrics?.max_drawdown || 0) * 100).toFixed(2)}%`} 
                  icon={<TrendingDown className="text-red-500" />} 
                  trend={`Recovery: ${results.metrics?.max_dd_duration_days || 0} days`}
                  valueClassName="text-red-500"
                />
                <MetricCard 
                  title="Sharpe Ratio" 
                  value={(results.metrics?.sharpe || 0).toFixed(2)} 
                  icon={<Activity className="text-accent" />} 
                  trend="Risk-adjusted Return"
                  valueClassName="text-accent"
                />
                <MetricCard 
                  title="95% Daily VaR" 
                  value={`${((results.metrics?.var_95 || 0) * 100).toFixed(2)}%`} 
                  icon={<ShieldAlert className="text-orange-500" />} 
                  trend="Probable Tail Risk"
                  valueClassName="text-orange-500"
                />
             </div>

             {/* ROW 2: Charts */}
             <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 glass-panel p-6 rounded-2xl h-[450px]">
                  <h3 className="text-lg font-bold mb-6 flex items-center gap-2"><Activity size={18} className="text-accent" /> HISTORICAL DRAWDOWN CURVE</h3>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={results.drawdown_curve}>
                      <defs>
                        <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2}/>
                          <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                      <XAxis dataKey="date" stroke="rgba(255,255,255,0.4)" fontSize={10} minTickGap={100} />
                      <YAxis stroke="rgba(255,255,255,0.4)" fontSize={10} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1a1a2e', border: 'none', borderRadius: '12px', fontSize: '12px' }}
                        itemStyle={{ color: '#ef4444' }}
                      />
                      <Area type="monotone" dataKey="drawdown" stroke="#ef4444" fillOpacity={1} fill="url(#colorRisk)" strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>

                <div className="glass-panel p-6 rounded-2xl flex flex-col h-[450px]">
                   <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-6">Asset Correlation Matrix</h3>
                   <div className="flex-1 grid grid-cols-3 grid-rows-3 gap-1">
                      {results.correlation_matrix.map((item: any, i: number) => (
                        <div key={i} className="group relative flex items-center justify-center rounded-md text-[10px] font-mono font-bold" 
                             style={{ backgroundColor: `rgba(0, 212, 255, ${Math.abs(item.v)})` }}>
                           <span className={cn(Math.abs(item.v) > 0.6 ? "text-black" : "text-white/40 group-hover:text-white")}>{item.v.toFixed(2)}</span>
                           {/* Hover Ticker Info */}
                           <div className="absolute -top-10 scale-0 group-hover:scale-100 bg-black border border-white/10 px-2 py-1 rounded text-white pointer-events-none transition-all z-20 whitespace-nowrap">
                             {item.x} vs {item.y}
                           </div>
                        </div>
                      ))}
                   </div>
                   <div className="mt-4 flex justify-between items-center text-[10px] text-gray-600 font-bold uppercase tracking-widest">
                      <span>Low Corr</span>
                      <div className="flex-1 mx-4 h-1 rounded-full bg-gradient-to-r from-white/5 to-accent" />
                      <span>High Corr</span>
                   </div>
                </div>
             </div>

             {/* ROW 3: Stress Tests & Factors */}
             <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pb-12">
                <div className="glass-panel p-6 rounded-2xl">
                  <h3 className="text-lg font-bold mb-6">Scenario Stress Testing</h3>
                  <div className="grid grid-cols-1 gap-4">
                    {(scenarios || []).map((scen: any, i: number) => (
                      <div key={i} className="p-4 rounded-xl bg-surface border border-white/5 hover:border-white/20 transition-all">
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <span className="text-[10px] font-bold text-accent uppercase tracking-widest">{scen.type}</span>
                            <h4 className="text-sm font-bold text-white">{scen.name}</h4>
                          </div>
                          <div className={cn("text-lg font-mono font-bold", scen.your_portfolio_impact < 0 ? "text-red-500" : "text-green-500")}>
                            {(scen.your_portfolio_impact * 100).toFixed(1)}%
                          </div>
                        </div>
                        <div className="flex gap-2 flex-wrap">
                           {(scen.most_affected_positions || []).slice(0, 3).map((pos: any, j: number) => (
                             <span key={j} className="text-[9px] px-2 py-0.5 rounded bg-white/5 text-gray-500">{pos.ticker}: {(pos.impact * 100).toFixed(1)}%</span>
                           ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="glass-panel p-6 rounded-2xl flex flex-col h-full">
                  <h3 className="text-lg font-bold mb-6">Factor Exposure (Fama-French)</h3>
                  <div className="flex-1 space-y-6">
                    {factors && Object.entries(factors.betas).map(([factor, value]: [string, any], i: number) => (
                      <div key={i} className="space-y-2">
                        <div className="flex justify-between text-[10px] font-bold uppercase">
                          <span className="text-gray-400">{factor}</span>
                          <span className={cn(value > 1 ? "text-accent" : "text-white")}>{value.toFixed(2)}</span>
                        </div>
                        <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                           <motion.div 
                            initial={{ width: 0 }}
                            animate={{ width: `${Math.min(Math.abs(value) * 50, 100)}%` }}
                            className={cn("h-full", value > 0 ? "bg-accent" : "bg-red-500")}
                           />
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-8 p-4 rounded-xl bg-accent/5 border border-accent/10">
                     <p className="text-[10px] text-gray-400 leading-relaxed">
                        A Market Beta of <span className="text-white font-bold">{factors?.betas.Market?.toFixed(2)}</span> indicates your portfolio is {Math.abs(factors?.betas.Market - 1) * 100}% {factors?.betas.Market > 1 ? 'more' : 'less'} volatile than the S&P 500.
                     </p>
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
