"use client";

import { useState, useEffect, useRef } from "react";
import { BrainCircuit, Activity, TrendingUp, TrendingDown, Minus, Cpu, ShieldAlert, Newspaper, Info, AlertTriangle } from "lucide-react";
import { motion } from "framer-motion";
import { apiFetch, getAuthHeaders } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, CartesianGrid, ReferenceLine, Cell, LabelList } from "recharts";
import { ChartSkeleton } from "@/components/ui/ChartSkeleton";
import { TickerChip } from "@/components/ui/TickerChip";
import { useToast } from "@/components/ui/Toast";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

import { useMarketStore } from "@/lib/market-store";

export default function SignalsPage() {
  const { activeTicker: ticker, setActiveTicker: setTicker } = useMarketStore();
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMsg, setStatusMsg] = useState("");
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  
  const [scanResults, setScanResults] = useState<any[]>([]);
  const [scanning, setScanning] = useState(false);
  const [scanError, setScanError] = useState(false);
  const [historyData, setHistoryData] = useState<any[]>([]);
  const { toast } = useToast();
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const authFailCountRef = useRef(0);

  useEffect(() => {
    runScan();
    return () => { if (pollingRef.current) clearInterval(pollingRef.current); };
  }, []);

  const runScan = async () => {
    setScanning(true);
    setScanError(false);
    try {
      const data = await apiFetch("/signals/scan");
      setScanResults(data.scan_results || []);
    } catch (err) {
      console.error(err);
      setScanError(true);
    } finally {
      setScanning(false);
    }
  };

  /**
   * Starts polling for signal job results with robust auth handling.
   * Utilizes the central apiFetch helper for automatic token management and refreshes.
   */
  const startPolling = (jobId: string) => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    
    const intervalId = setInterval(async () => {
      try {
        const data = await apiFetch(`/signals/status/${jobId}`);
        
        if (data.progress !== undefined) setProgress(data.progress);
        if (data.status) setStatusMsg(data.status);
        
        if (data.status === 'complete') {
          clearInterval(intervalId);
          if (pollingRef.current === intervalId) {
            pollingRef.current = null;
          }
          setResult(data.result);
          setLoading(false);
          toast({ type: 'success', title: 'Signals Generated', description: `AI Ensemble output for ${ticker} is ready.` });
        } else if (data.status === 'error') {
          clearInterval(intervalId);
          if (pollingRef.current === intervalId) {
            pollingRef.current = null;
          }
          setError(data.message || "Pipeline failed");
          setLoading(false);
        }
      } catch (e: any) {
        console.error("Polling error:", e);
        if (e.message === "Session expired") {
          clearInterval(intervalId);
          if (pollingRef.current === intervalId) {
            pollingRef.current = null;
          }
          setError("Authentication session expired. Please sign out and sign in again.");
          setLoading(false);
          toast({ 
            type: 'error', 
            title: 'Session Expired', 
            description: 'Unable to refresh your session. Polling stopped.' 
          });
        }
      }
    }, 2000);
    
    pollingRef.current = intervalId;
    
    setTimeout(() => {
      clearInterval(intervalId);
      if (pollingRef.current === intervalId) {
        pollingRef.current = null;
      }
      setLoading(prev => {
        if (prev) { setError("Request timed out."); return false; }
        return prev;
      });
    }, 240000);
  };

  const runPrediction = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setProgress(0);
    setStatusMsg("Initializing Neural Networks...");

    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/signals/predict`, {
        method: "POST",
        headers,
        body: JSON.stringify({ ticker }),
      });

      if (response.status === 401 || response.status === 403) {
        const refreshedHeaders = await getAuthHeaders(true);
        const retryRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/signals/predict`, {
          method: "POST",
          headers: refreshedHeaders,
          body: JSON.stringify({ ticker }),
        });
        if (!retryRes.ok) throw new Error(`Auth failed (${retryRes.status}). Please sign in again.`);
        const retryData = await retryRes.json();
        if (!retryData.job_id) throw new Error("Failed to start signal job");
        startPolling(retryData.job_id);
        return;
      }

      const { job_id } = await response.json();
      if (!job_id) throw new Error("Failed to start signal job");
      startPolling(job_id);

    } catch (err: any) {
      setError(err.message || "Failed to run prediction pipeline");
      toast({ type: 'error', title: 'Pipeline Failed', description: err.message });
      setLoading(false);
    }
  };

  const getSignalColor = (signal: string) => {
    if (signal === "BUY") return "text-accent border-accent/20 bg-accent/5";
    if (signal === "SELL") return "text-red-500 border-red-500/20 bg-red-500/5";
    return "text-gray-400 border-white/10 bg-white/5";
  };

  useEffect(() => {
    if (!ticker || !result) return;
    let isMounted = true;

    const loadHistory = async () => {
      try {
        const data = await apiFetch(`/stocks/${ticker}/history?period=1mo`);
        const history = (data.data || []).slice(-20).map((point: any) => ({
          label: point.time,
          price: point.close,
          isPrediction: false,
        }));
        const predictedPrice = result.signal_breakdown?.lstm?.predicted_price || result.current_price;
        const predictionPoint = { label: "Forecast", price: predictedPrice, isPrediction: true };
        if (isMounted) setHistoryData([...history, predictionPoint]);
      } catch {
        if (isMounted) setHistoryData([]);
      }
    };

    loadHistory();
    return () => {
      isMounted = false;
    };
  }, [ticker, result]);

  const [forecastHorizon, setForecastHorizon] = useState(30);

  const WeightBar = ({ weight, color }: { weight: number; color: string }) => (
    <div style={{ display:'flex', alignItems:'center', gap:6 }}>
      <div style={{ width:60, height:4, background:'var(--color-border-tertiary)',
        borderRadius:2, overflow:'hidden' }}>
        <div style={{
          height:'100%', width:`${weight}%`,
          background: color, borderRadius:2
        }} />
      </div>
      <span style={{ fontSize:12, color:'var(--color-text-secondary)',
        fontWeight:500 }}>{weight}%</span>
    </div>
  );

  const SentimentRow = ({ label, value }: { label: string, value: number }) => {
    const isZero = Math.abs(value) < 0.01;
    const isPositive = value > 0;
    const widthPercent = Math.min(Math.abs(value) * 100, 100);

    return (
      <div className="flex flex-col gap-1.5 font-mono text-[11px] w-full">
        <div className="flex justify-between items-center text-[10px]">
          <span className="text-gray-400 font-bold">{label}</span>
          <span className={cn("font-bold", isZero ? "text-gray-400" : isPositive ? "text-green-500" : "text-red-500")}>
            {value > 0 ? "+" : ""}{value.toFixed(2)}
          </span>
        </div>
        <div className="h-3 w-full bg-white/5 rounded-full overflow-hidden flex relative border border-white/5">
          <div className="absolute top-0 bottom-0 left-1/2 w-[1px] bg-white/20 z-10" />
          {isZero ? (
            <div className="absolute inset-0 bg-gray-500/10 border border-dashed border-gray-500/40 rounded-full" />
          ) : isPositive ? (
            <div 
              className="h-full bg-green-500 transition-all rounded-r-full" 
              style={{ width: `${widthPercent / 2}%`, marginLeft: '50%' }} 
            />
          ) : (
            <div 
              className="h-full bg-red-500 transition-all ml-auto rounded-l-full" 
              style={{ width: `${widthPercent / 2}%`, marginRight: '50%' }} 
            />
          )}
        </div>
      </div>
    );
  };

  const PipelineStep = ({ label, state }: { label: string, state: "pending" | "active" | "done" }) => {
    return (
      <div className="flex items-center gap-3 font-mono text-xs">
        <div className="flex items-center justify-center w-5 h-5 shrink-0">
          {state === "done" && (
            <span className="w-5 h-5 rounded-full bg-green-500/10 border border-green-500 text-green-500 flex items-center justify-center font-bold text-[10px]">✓</span>
          )}
          {state === "active" && (
            <span className="w-5 h-5 rounded-full bg-accent/10 border border-accent text-accent flex items-center justify-center font-bold text-[10px] animate-spin">●</span>
          )}
          {state === "pending" && (
            <span className="w-5 h-5 rounded-full bg-card border border-white/10 text-gray-500 flex items-center justify-center font-bold text-[10px]">○</span>
          )}
        </div>
        <span className={cn(
          state === "done" && "text-green-500",
          state === "active" && "text-accent font-bold",
          state === "pending" && "text-gray-500"
        )}>
          {label}{state === "active" ? "..." : ""}
        </span>
      </div>
    );
  };

  const getConfColorClass = (conf: number) => {
    if (conf >= 70) return "text-green-500";
    if (conf >= 50) return "text-amber-500";
    return "text-red-500";
  };

  const todayLabel = historyData.filter(d => !d.isPrediction).slice(-1)[0]?.label;

  const newsSentiment = result?.signal_breakdown?.sentiment?.news_sentiment ?? result?.signal_breakdown?.sentiment?.score ?? 0;
  const socialSentiment = result?.signal_breakdown?.sentiment?.social_sentiment ?? (result?.signal_breakdown?.sentiment?.score ? result.signal_breakdown.sentiment.score * 0.8 : 0);
  const earningsTone = result?.signal_breakdown?.sentiment?.earnings_tone ?? (result?.signal_breakdown?.sentiment?.score ? result.signal_breakdown.sentiment.score * 0.9 : 0);
  const analystSentiment = result?.signal_breakdown?.sentiment?.analyst_sentiment ?? (result?.signal_breakdown?.sentiment?.score ? result.signal_breakdown.sentiment.score * 0.75 : 0);

  const allSentimentsZero = Math.abs(newsSentiment) < 0.01 && 
                            Math.abs(socialSentiment) < 0.01 && 
                            Math.abs(earningsTone) < 0.01 && 
                            Math.abs(analystSentiment) < 0.01;

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto w-full pb-12">
      {/* TOP: Page title & actions */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <BrainCircuit className="text-accent" /> AI Signals
          </h1>
          <TickerChip ticker={ticker} onClear={() => setTicker("")} />
          {loading && ticker ? (
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '4px 12px',
              background: 'var(--color-background-warning)',
              border: '0.5px solid var(--color-border-warning)',
              borderRadius: 999,
              fontSize: 12,
              fontWeight: 500,
              color: 'var(--color-text-warning)'
            }}>
              <i className="ti ti-loader-2" aria-hidden="true"
                style={{ fontSize: 14, display: 'inline-block', animation: 'spin 1s linear infinite' }} />
              <span>ANALYZING: {ticker}</span>
              <button onClick={() => {
                setLoading(false);
                if (pollingRef.current) {
                  clearInterval(pollingRef.current);
                  pollingRef.current = null;
                }
              }} aria-label="Cancel pipeline"
                style={{ background: 'none', border: 'none', cursor: 'pointer',
                  padding: 0, display: 'flex', color: 'inherit' }}>
                <i className="ti ti-x" style={{ fontSize: 14 }} />
              </button>
              <style>{`
                @keyframes spin {
                  to { transform: rotate(360deg); }
                }
              `}</style>
            </div>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
           <Button 
            onClick={runPrediction} 
            disabled={loading}
            className="bg-accent hover:bg-accent/90 text-white gap-2 px-6"
            aria-busy={loading}
          >
            {loading ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin shrink-0" />
                RUNNING...
              </>
            ) : (
              <><Cpu size={16} fill="currentColor" /> RUN AI PIPELINE</>
            )}
          </Button>
        </div>
      </div>

      {/* BELOW: Configuration/Scanner panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="glass-panel rounded-2xl overflow-hidden flex flex-col h-[300px]">
          <div className="p-4 border-b border-white/5 flex justify-between items-center bg-surface/50">
            <h3 className="font-bold text-xs uppercase tracking-wider text-gray-400">Signal Scanner</h3>
            <Button variant="ghost" size="sm" onClick={runScan} loading={scanning} className="h-6 text-[10px]">
              {scanning ? "" : "REFRESH"}
            </Button>
          </div>
          <div className="flex-1 overflow-auto p-4 flex flex-col justify-center">
            {scanning ? (
              <div className="space-y-4 py-2 w-full">
                {[1, 2, 3].map(i => (
                  <div key={i} className="flex items-center justify-between animate-pulse">
                    <div className="h-3.5 bg-white/10 rounded w-16" />
                    <div className="h-5 bg-white/10 rounded w-12" />
                    <div className="h-3.5 bg-white/10 rounded w-8" />
                  </div>
                ))}
              </div>
            ) : scanError ? (
              <div className="flex flex-col items-center justify-center text-center p-4 gap-2 my-auto">
                <AlertTriangle className="text-red-500" size={24} />
                <p className="text-xs text-gray-400">Signal scan failed</p>
                <Button size="sm" variant="outline" className="h-7 text-[10px] mt-1 text-white border-white/10" onClick={runScan}>
                  Retry
                </Button>
              </div>
            ) : scanResults.length === 0 ? (
              <div className="flex flex-col items-center justify-center text-center p-4 gap-2 my-auto">
                <Activity className="text-gray-500 opacity-40 animate-pulse" size={28} />
                <p className="font-bold text-xs text-white">No signals detected</p>
                <p className="text-[10px] text-gray-500 max-w-[200px] leading-relaxed">
                  Try running the pipeline with a different ticker or timeframe.
                </p>
              </div>
            ) : (
              <table className="w-full text-[11px] text-left font-mono my-auto">
                <thead className="text-gray-500 uppercase">
                  <tr>
                    <th className="pb-3">Asset</th>
                    <th className="pb-3">Signal</th>
                    <th className="pb-3 text-right">Conf</th>
                  </tr>
                </thead>
                <tbody>
                  {scanResults.map((r, i) => (
                    <tr key={i} className="border-b border-white/5 hover:bg-white/5 cursor-pointer group" onClick={() => setTicker(r.ticker)}>
                      <td className="py-2.5 font-bold text-white group-hover:text-accent transition-colors">{r.ticker}</td>
                      <td className="py-2.5">
                        <span className={`px-2 py-0.5 rounded border text-[10px] font-bold ${getSignalColor(r.signal)}`}>
                          {r.signal}
                        </span>
                      </td>
                      <td className={`py-2.5 text-right font-bold ${getConfColorClass(r.confidence)}`}>
                        {(r.confidence || 0).toFixed(0)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="lg:col-span-2 glass-panel p-6 rounded-2xl flex flex-col justify-center gap-6">
          <div className="space-y-2">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Info size={16} className="text-accent" /> Model Pipeline Status
            </h3>
            <p className="text-xs text-gray-500">
              Generating an ensemble signal involves training LSTM for sequence prediction, XGBoost for trend classification, and NLP models for sentiment analysis.
            </p>
          </div>
          
          {loading ? (
            <div className="space-y-4">
              <div className="space-y-3.5 py-2 border-l-2 border-white/5 ml-2.5 pl-6 relative">
                <PipelineStep 
                  label="Training LSTM sequence model" 
                  state={progress > 40 ? "done" : progress > 0 ? "active" : "pending"} 
                />
                <PipelineStep 
                  label="Running XGBoost classifier" 
                  state={progress > 75 ? "done" : progress > 40 ? "active" : "pending"} 
                />
                <PipelineStep 
                  label="Scoring NLP sentiment" 
                  state={progress >= 100 ? "done" : progress > 75 ? "active" : "pending"} 
                />
              </div>
              <div className="space-y-2 pt-2">
                <div className="flex justify-between items-end">
                  <span className="text-sm font-mono text-accent animate-pulse">{statusMsg}</span>
                  <span className="text-xl font-bold font-mono text-white">{progress}%</span>
                </div>
                <Progress value={progress} className="h-2 bg-white/5" />
                <p className="text-[10px] text-gray-600 italic">Estimated time: ~12s per ticker</p>
              </div>
            </div>
          ) : result ? (
            <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/20 text-green-500 text-xs font-mono font-bold flex items-center gap-2">
              <span>✓ Pipeline complete — signals ready</span>
            </div>
          ) : !error ? (
            <div className="flex items-center justify-center h-32 border border-dashed border-white/10 rounded-xl">
               <span className="text-sm text-gray-500">Configure parameters and click &quot;RUN AI PIPELINE&quot; to begin</span>
            </div>
          ) : null}
          
          {error && <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 text-sm flex gap-3">
            <AlertTriangle size={18} className="shrink-0" />
            <span>{error}</span>
          </div>}
        </div>
      </div>

      {/* MAIN: Results Area */}
      <div className="min-h-[600px] flex flex-col gap-6">
        {loading ? (
          <div className="flex flex-col gap-6">
            <div className="h-[200px] bg-white/5 rounded-2xl animate-pulse" />
            <div className="grid grid-cols-2 gap-6">
              <ChartSkeleton type="line" className="h-[250px]" />
              <ChartSkeleton type="bar" className="h-[250px]" />
            </div>
          </div>
        ) : result ? (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-6">
            {/* HERO SIGNAL CARD */}
            <div className="glass-panel p-8 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-8 bg-[#0d0d14] relative overflow-hidden">
               <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-accent/30 to-transparent" />
               
               <div className="flex items-center gap-8">
                 <div 
                   className={cn(
                     "w-24 h-24 rounded-full flex items-center justify-center border-2 transition-all cursor-help relative group",
                     result.final_signal === 'BUY' ? 'border-green-500 text-green-500 bg-green-500/5' : 
                     result.final_signal === 'SELL' ? 'border-red-500 text-red-500 bg-red-500/5' : 
                     'border-amber-500 text-amber-500 bg-amber-500/5'
                   )}
                   aria-label="Ensemble signal: aggregated from LSTM (40%), XGBoost (35%), NLP (25%)"
                 >
                   {result.final_signal === 'BUY' ? <TrendingUp size={48} className="fill-green-500/20" /> : 
                    result.final_signal === 'SELL' ? <TrendingDown size={48} className="fill-red-500/20" /> : 
                    <Minus size={48} className="fill-amber-500/20" />}
                   
                   {/* Tooltip on hover */}
                   <div className="absolute bottom-full mb-2 hidden group-hover:block w-64 bg-card border border-border p-2.5 rounded-xl text-[10px] text-gray-500 leading-relaxed font-mono shadow-2xl z-50 text-center">
                     Ensemble signal: aggregated from LSTM (40%), XGBoost (35%), NLP (25%)
                   </div>
                 </div>
                 <div>
                    <h2 className="text-sm font-mono text-gray-500 uppercase tracking-[0.2em] mb-1">Ensemble Decision</h2>
                    <div className="flex items-baseline gap-3">
                      <span className={cn(
                        "text-7xl font-bold tracking-tighter",
                        result.final_signal === 'BUY' ? 'text-green-500' : 
                        result.final_signal === 'SELL' ? 'text-red-500' : 'text-amber-500'
                      )}>
                        {result.final_signal}
                      </span>
                      <span className="text-3xl font-mono font-bold text-white/20">@{(result.confidence || 0).toFixed(1)}%</span>
                    </div>
                    {/* Threshold Legend */}
                    <div className="text-[11px] font-mono text-gray-500 mt-1 select-none">
                      <span className="text-green-500 font-bold">BUY ≥ 70%</span>  |  <span className="text-amber-500 font-bold">HOLD 45–69%</span>  |  <span className="text-red-500 font-bold">SELL &lt; 45%</span>
                    </div>
                 </div>
               </div>

               <div className="grid grid-cols-2 gap-8 border-l border-white/5 pl-8 h-24 items-center">
                  <div className="text-center">
                    <p className="text-[10px] text-gray-500 uppercase font-bold mb-1">Vol Regime</p>
                    <p className="text-lg font-bold text-white uppercase">{result.risk_assessment?.volatility || "normal"}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-[10px] text-gray-500 uppercase font-bold mb-1">Position Size</p>
                    <p className="text-lg font-bold text-accent">{(result.risk_assessment?.suggested_position_size_pct || 0).toFixed(1)}%</p>
                  </div>
               </div>
            </div>

            {/* EXPLAINABILITY GRID */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              
              {/* LSTM MODULE */}
              <div className="glass-panel p-6 rounded-2xl flex flex-col gap-4 bg-[#0d0d14]">
                <div className="flex justify-between items-center">
                   <h3 className="font-bold text-sm flex items-center gap-2"><Cpu size={16} className="text-accent" /> LSTM Sequence Analysis</h3>
                   <div className="flex items-center gap-3">
                    <select 
                      value={forecastHorizon}
                      onChange={e => setForecastHorizon(Number(e.target.value))}
                      className="bg-card border border-white/10 rounded px-1.5 py-0.5 text-[9px] font-bold text-gray-500 outline-none cursor-pointer"
                    >
                      <option value="7">7d ▾</option>
                      <option value="14">14d ▾</option>
                      <option value="30">30d ▾</option>
                      <option value="60">60d ▾</option>
                    </select>
                    <WeightBar weight={40} color="#378ADD" />
                  </div>
                </div>
                <div className="h-[300px] w-full" style={{ minHeight: 300, minWidth: 0 }}>
                   {historyData && historyData.length > 0 && (
                     <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={300}>
                       <LineChart data={historyData}>
                         <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                         <XAxis 
                           dataKey="label" 
                           tickFormatter={(val) => {
                             if (!val) return "";
                             if (val === "Forecast") return "Forecast";
                             const d = new Date(val);
                             if (isNaN(d.getTime())) return val;
                             return `${d.getMonth()+1}/${d.getDate()}`;
                           }}
                           tick={{ fontSize: 10, fill: 'var(--color-text-secondary)' }}
                            minTickGap={25}
                           angle={-35}
                           textAnchor="end"
                           height={40}
                           tickLine={false}
                           axisLine={false}
                         />
                         <YAxis domain={['auto', 'auto']} hide />
                         <Tooltip 
                           content={({ active, payload }) => {
                             if (active && payload && payload.length) {
                               const data = payload[0].payload;
                               const price = data.price || 0;
                               if (data.isPrediction) {
                                 const change = (result.signal_breakdown?.lstm?.expected_return || 0) * 100;
                                 return (
                                   <div style={{
                                     background: 'var(--color-background-primary)',
                                     border: '0.5px solid var(--color-border-secondary)',
                                     borderRadius: 'var(--border-radius-md)',
                                     padding: '8px 12px',
                                     fontSize: 12,
                                     fontFamily: 'monospace'
                                   }}>
                                     <span>
                                       Forecast Price: <strong>${price.toFixed(2)}</strong>
                                       <span style={{
                                         color: change < 0
                                           ? 'var(--color-text-danger)'
                                           : 'var(--color-text-success)'
                                       }}>
                                         {' '}({change > 0 ? '+' : ''}{change.toFixed(2)}%)
                                       </span>
                                       <span style={{ color: 'var(--color-text-tertiary)' }}>
                                         {' · '}{forecastHorizon}d forecast
                                       </span>
                                     </span>
                                   </div>
                                 );
                               } else {
                                 return (
                                   <div style={{
                                     background: 'var(--color-background-primary)',
                                     border: '0.5px solid var(--color-border-secondary)',
                                     borderRadius: 'var(--border-radius-md)',
                                     padding: '8px 12px',
                                     fontSize: 12,
                                     fontFamily: 'monospace'
                                   }}>
                                     <span>Price: <strong>${price.toFixed(2)}</strong></span>
                                   </div>
                                 );
                               }
                             }
                             return null;
                           }}
                           wrapperStyle={{ zIndex: 10 }}
                         />
                         <Line type="monotone" dataKey="price" stroke="rgba(255,255,255,0.3)" strokeWidth={2} dot={false} />
                         <Line type="monotone" dataKey="price" data={historyData.filter(d => d.isPrediction)} stroke="#00d4ff" strokeWidth={2} strokeDasharray="5 5" dot={false} activeDot={{ r: 6, fill: '#fff', stroke: '#00d4ff', strokeWidth: 2 }} />
                         {todayLabel && (
                           <ReferenceLine 
                             x={todayLabel} 
                             stroke="var(--accent-teal)" 
                             strokeDasharray="3 3" 
                             label={{ value: 'TODAY', fill: 'var(--accent-teal)', fontSize: 9, position: 'top', fontWeight: 'bold' }} 
                           />
                         )}
                       </LineChart>
                     </ResponsiveContainer>
                   )}
                 </div>
                 <div className="flex justify-center gap-4 text-[10px] font-mono text-gray-500 mt-2">
                   <span className="flex items-center gap-1.5"><span className="w-4 h-[2px] bg-white/20" /> Historical</span>
                   <span className="flex items-center gap-1.5"><span className="w-4 h-[2px] border-t-2 border-dashed border-[#00d4ff]" /> Forecast</span>
                 </div>
                 <div className="p-3 rounded-lg bg-white/5 border border-white/5 mt-10">
                    <p className="text-xs text-gray-400 leading-relaxed italic">
                      Forecast Price: <strong className="text-white">${(result.signal_breakdown?.lstm?.predicted_price || 0).toFixed(2)}</strong>
                      <span className={((result.signal_breakdown?.lstm?.expected_return || 0) >= 0) ? "text-green-500 font-bold ml-1.5" : "text-red-500 font-bold ml-1.5"}>
                        ({((result.signal_breakdown?.lstm?.expected_return || 0) >= 0 ? '+' : '')}{((result.signal_breakdown?.lstm?.expected_return || 0) * 100).toFixed(2)}%)
                      </span>
                      <span style={{ color: 'var(--color-text-tertiary)', marginLeft: 8 }}>
                        · {forecastHorizon}d forecast
                      </span>
                    </p>
                  </div>
              </div>

              {/* XGBOOST MODULE */}
              <div className="glass-panel p-6 rounded-2xl flex flex-col gap-4 bg-[#0d0d14]">
                  <div className="flex justify-between items-center">
                    <h3 className="font-bold text-sm flex items-center gap-2"><Activity size={16} className="text-purple-500" /> Model Conviction</h3>
                    <WeightBar weight={35} color="#1D9E75" />
                  </div>
                <div className="h-[300px] w-full" style={{ minHeight: 300, minWidth: 0 }}>
                    {result.signal_breakdown && (
                      <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={300}>
                        <BarChart data={[
                          { name: 'LSTM', val: Math.abs(result.signal_breakdown?.model_scores?.lstm_expected_return_pct || 0) },
                          { name: 'XGB', val: (result.signal_breakdown?.model_scores?.xgboost_confidence_pct || 0) },
                          { name: 'NLP', val: Math.abs((result.signal_breakdown?.model_scores?.sentiment_score || 0) * 100) }
                        ]} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                          <XAxis dataKey="name" stroke="rgba(255,255,255,0.5)" fontSize={10} />
                          <YAxis 
                            domain={[0, 100]} 
                            stroke="rgba(255,255,255,0.5)" 
                            fontSize={10} 
                            label={{ value: 'Confidence (%)', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle', fill: 'rgba(255,255,255,0.5)', fontSize: 10 } }} 
                          />
                          <Tooltip contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }} />
                          <Bar dataKey="val" radius={[4, 4, 0, 0]} barSize={40} fillOpacity={0.85}>
                            {
                              [
                                { fill: "#378ADD" }, // LSTM (blue)
                                { fill: "#1D9E75" }, // XGB (teal)
                                { fill: "#7F77DD" }  // NLP (purple)
                              ].map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.fill} />
                              ))
                            }
                            <LabelList dataKey="val" position="top" formatter={(v: any) => `${Number(v).toFixed(1)}%`} style={{ fontSize: 10, fill: "rgba(255,255,255,0.8)", fontWeight: "bold" }} />
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    )}
                </div>

                  <div className="p-3 rounded-lg bg-white/5 border border-white/5 mt-10">
                    <p className="text-xs text-gray-400 leading-relaxed italic">
                      Trend Prediction: <strong className="text-white">{result.signal_breakdown?.xgboost?.trend || "NEUTRAL"}</strong>
                      <span className={(result.signal_breakdown?.xgboost?.trend === 'BUY' || result.signal_breakdown?.xgboost?.trend === 'BULLISH') ? "text-green-500 font-bold ml-1.5" : (result.signal_breakdown?.xgboost?.trend === 'SELL' || result.signal_breakdown?.xgboost?.trend === 'BEARISH') ? "text-red-500 font-bold ml-1.5" : "text-gray-400 font-bold ml-1.5"}>
                        ({((result.signal_breakdown?.xgboost?.confidence || 0) * 100).toFixed(1)}% confidence)
                      </span>
                    </p>
                  </div>
              </div>

              {/* SENTIMENT MODULE */}
              <div className="glass-panel p-6 rounded-2xl flex flex-col gap-4 bg-[#0d0d14]">
                  <div className="flex justify-between items-center">
                    <h3 className="font-bold text-sm flex items-center gap-2"><Newspaper size={16} className="text-blue-500" /> NLP Sentiment Score</h3>
                    <WeightBar weight={25} color="#7F77DD" />
                  </div>                  <div className="flex-1 flex flex-col justify-center py-2">
                    <div className="space-y-4 w-full">
                      {[
                        { label: 'News Sentiment',        key: 'news',     val: allSentimentsZero ? 0 : newsSentiment },
                        { label: 'Social Sentiment',      key: 'social',   val: allSentimentsZero ? 0 : socialSentiment },
                        { label: 'Earnings Call Tone',    key: 'earnings', val: allSentimentsZero ? 0 : earningsTone },
                        { label: 'Analyst Revision',      key: 'analyst',  val: allSentimentsZero ? 0 : analystSentiment },
                      ].map(row => {
                        const val = row.val;
                        const pct = Math.min(Math.abs(val) * 100, 100);
                        const isPositive = val >= 0;
                        const isZero = allSentimentsZero || Math.abs(val) < 0.01;

                        return (
                          <div key={row.key} style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 10,
                            padding: '6px 0',
                            borderBottom: '0.5px solid var(--color-border-tertiary)'
                          }}>
                            <span style={{
                              fontSize: 12,
                              color: 'var(--color-text-secondary)',
                              width: 140,
                              flexShrink: 0
                            }}>{row.label}</span>

                            {isZero ? (
                              <div style={{
                                flex: 1,
                                height: 4,
                                background: 'var(--color-border-tertiary)',
                                borderRadius: 2,
                                border: '0.5px dashed var(--color-border-secondary)'
                              }} />
                            ) : (
                              <div style={{
                                flex: 1,
                                height: 6,
                                background: 'var(--color-border-tertiary)',
                                borderRadius: 3,
                                overflow: 'hidden'
                              }}>
                                <div style={{
                                  height: '100%',
                                  width: `${pct}%`,
                                  background: isPositive
                                    ? 'var(--color-background-success)'
                                    : 'var(--color-background-danger)',
                                  borderRadius: 3
                                }} />
                              </div>
                            )}

                            <span style={{
                              fontSize: 12,
                              fontWeight: 500,
                              width: 36,
                              textAlign: 'right',
                              color: isZero
                                ? 'var(--color-text-tertiary)'
                                : isPositive
                                  ? 'var(--color-text-success)'
                                  : 'var(--color-text-danger)'
                            }}>
                              {isZero ? '—' : (isPositive ? '+' : '') + val.toFixed(2)}
                            </span>
                          </div>
                        );
                      })}
                      
                      <div className="flex justify-between text-[9px] text-gray-500 font-mono pt-1">
                        <span>BEARISH (-1.0)</span>
                        <span>NEUTRAL (0.0)</span>
                        <span>BULLISH (+1.0)</span>
                      </div>
                    </div>

                    {allSentimentsZero && (
                      <div style={{
                        marginTop: 12,
                        padding: '10px 12px',
                        background: 'var(--color-background-warning)',
                        border: '0.5px solid var(--color-border-warning)',
                        borderRadius: 'var(--border-radius-md)',
                        fontSize: 13,
                        color: 'var(--color-text-warning)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8
                      }}>
                        <i className="ti ti-alert-triangle" aria-hidden="true"
                          style={{ fontSize: 16, flexShrink: 0 }} />
                        Sentiment data unavailable — no recent news found for this ticker.
                      </div>
                    )}
                  </div>
                 </div>

              {/* STRATEGIC EXECUTION & RISK ASSESSMENT */}
              <div className="glass-panel p-6 rounded-2xl flex flex-col gap-4 bg-[#0d0d14]">
                 <h3 className="font-bold text-sm flex items-center gap-2"><ShieldAlert size={16} className="text-amber-500" /> Strategic Execution</h3>
                 <div className="grid grid-cols-2 gap-4 flex-1">
                     <div style={{
                       background: 'var(--color-background-secondary)',
                       border: '0.5px solid var(--color-border-tertiary)',
                       borderRadius: 'var(--border-radius-md)',
                       padding: '1rem',
                       display: 'flex',
                       flexDirection: 'column',
                       justifyContent: 'space-between',
                       height: '6rem'
                     }}>
                        <p style={{
                          color: 'var(--color-text-secondary)',
                          fontSize: '12px',
                          fontWeight: 400,
                          textTransform: 'uppercase',
                          letterSpacing: '0.1em'
                        }}>Stop Loss</p>
                        <p style={{
                          color: 'var(--color-text-danger)',
                          fontSize: '24px',
                          fontWeight: 500,
                          fontFamily: 'monospace'
                        }}>
                          -{(result.risk_assessment?.suggested_stop_loss_pct || 0).toFixed(1)}%
                        </p>
                     </div>
                     
                     <div style={{
                       background: 'var(--color-background-secondary)',
                       border: '0.5px solid var(--color-border-tertiary)',
                       borderRadius: 'var(--border-radius-md)',
                       padding: '1rem',
                       display: 'flex',
                       flexDirection: 'column',
                       justifyContent: 'space-between',
                       height: '6rem',
                       position: 'relative'
                     }} className="group">
                        <div className="flex items-center gap-1.5 cursor-help">
                          <span style={{
                            color: 'var(--color-text-secondary)',
                            fontSize: '12px',
                            fontWeight: 400,
                            textTransform: 'uppercase',
                            letterSpacing: '0.1em'
                          }}>R:R Ratio</span>
                          <span className="text-gray-500 text-[10px]">ⓘ</span>
                          <div className="absolute bottom-full left-0 mb-2 hidden group-hover:block w-56 bg-card border border-border p-2.5 rounded-xl text-[10px] text-gray-500 leading-relaxed font-mono shadow-2xl z-50 text-left">
                            Reward-to-Risk Ratio: for every 1% risked, the model targets {(result.risk_assessment?.risk_reward_ratio || 0).toFixed(2)}% gain. A ratio above 2.0 is generally considered favorable.
                          </div>
                        </div>
                        <p style={{
                          color: (result.risk_assessment?.risk_reward_ratio || 0) >= 2.0 ? 'var(--color-text-success)' :
                                 (result.risk_assessment?.risk_reward_ratio || 0) >= 1.0 ? 'var(--color-text-warning)' : 'var(--color-text-danger)',
                          fontSize: '24px',
                          fontWeight: 500,
                          fontFamily: 'monospace'
                        }}>
                          {(result.risk_assessment?.risk_reward_ratio || 0).toFixed(2)}
                        </p>
                     </div>

                    <div className="col-span-2 p-4 rounded-xl border-l-[4px] border-[#EF9F27] bg-[#FAEEDA] flex gap-3 text-[13px] text-[#633806]">
                      <span className="text-lg shrink-0 mt-0.5">💡</span>
                      <div className="flex-1 space-y-3 font-mono">
                        <p className="font-bold border-b border-[#EF9F27]/20 pb-1.5 uppercase text-[11px] tracking-wider text-[#633806]/80">Model Recommendations</p>
                        
                        <div className="grid grid-cols-2 gap-y-2 text-xs">
                          <span className="font-medium text-[#633806]/70">Volatility Regime</span>
                          <span className="font-bold text-right uppercase">{result.risk_assessment?.volatility || "normal"}</span>
                          
                          <span className="font-medium text-[#633806]/70">Capital Allocation</span>
                          <span className="font-bold text-right">{(result.risk_assessment?.suggested_position_size_pct || 0).toFixed(1)}%</span>
                          
                          <span className="font-medium text-[#633806]/70">Reward Target</span>
                          <span className="font-bold text-right">{(result.risk_assessment?.reward_target_pct || 0).toFixed(1)}%</span>
                        </div>
                      </div>
                    </div>
                 </div>
              </div>

            </div>
          </motion.div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-600 opacity-50 border-2 border-dashed border-white/5 rounded-2xl min-h-[500px]">
            <BrainCircuit size={80} className="mb-4" />
            <h2 className="text-xl font-bold">Neural Engine Offline</h2>
            <p className="text-sm">Select a target and execute pipeline for real-time inference</p>
          </div>
        )}
      </div>
    </div>
  );
}
