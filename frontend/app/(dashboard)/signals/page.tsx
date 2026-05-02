"use client";

import { useState, useEffect } from "react";
import { BrainCircuit, Activity, TrendingUp, TrendingDown, Minus, Cpu, ShieldAlert, Newspaper, Info, AlertTriangle } from "lucide-react";
import { motion } from "framer-motion";
import { apiFetch, getAuthHeaders } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, CartesianGrid } from "recharts";
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
  const [historyData, setHistoryData] = useState<any[]>([]);
  const { toast } = useToast();

  useEffect(() => {
    runScan();
  }, []);

  const runScan = async () => {
    setScanning(true);
    try {
      const data = await apiFetch("/signals/scan");
      setScanResults(data.scan_results || []);
    } catch (err) {
      console.error(err);
    } finally {
      setScanning(false);
    }
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

      const { job_id } = await response.json();
      if (!job_id) throw new Error("Failed to start signal job");

      const poll = setInterval(async () => {
        try {
          const statusRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/signals/status/${job_id}`, {
            headers
          });
          const data = await statusRes.json();
          
          if (data.progress) setProgress(data.progress);
          if (data.status) setStatusMsg(data.status);
          
          if (data.status === 'complete') {
            clearInterval(poll);
            setResult(data.result);
            setLoading(false);
            toast({ type: 'success', title: 'Signals Generated', description: `AI Ensemble output for ${ticker} is ready.` });
          } else if (data.status === 'error') {
            clearInterval(poll);
            setError(data.message || "Pipeline failed");
            setLoading(false);
          }
        } catch (e) {
          console.error("Polling error:", e);
        }
      }, 2000);

      // Safety timeout after 60 seconds
      setTimeout(() => clearInterval(poll), 60000);

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

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto w-full pb-12">
      {/* TOP: Page title & actions */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <BrainCircuit className="text-accent" /> AI Signals
          </h1>
          <TickerChip ticker={ticker} onClear={() => setTicker("")} />
        </div>
        <div className="flex items-center gap-2">
           <Button 
            onClick={runPrediction} 
            loading={loading}
            className="bg-accent hover:bg-accent/90 text-white gap-2 px-6"
          >
            {loading ? "PROCESSING..." : <><Cpu size={16} fill="currentColor" /> RUN AI PIPELINE</>}
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
          <div className="flex-1 overflow-auto p-4">
            <table className="w-full text-[11px] text-left font-mono">
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
                    <td className="py-2.5 text-right text-gray-400">
                      {(r.confidence || 0).toFixed(0)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
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
          
          {loading && (
            <div className="space-y-4">
              <div className="flex justify-between items-end">
                <span className="text-sm font-mono text-accent animate-pulse">{statusMsg}</span>
                <span className="text-xl font-bold font-mono text-white">{progress}%</span>
              </div>
              <Progress value={progress} className="h-2 bg-white/5" />
              <p className="text-[10px] text-gray-600 italic">Estimated time: ~12s per ticker</p>
            </div>
          )}

          {!loading && !result && !error && (
            <div className="flex items-center justify-center h-32 border border-dashed border-white/10 rounded-xl">
               <span className="text-sm text-gray-500">Configure parameters and click &quot;RUN AI PIPELINE&quot; to begin</span>
            </div>
          )}
          
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
                 <div className={cn(
                   "w-24 h-24 rounded-full flex items-center justify-center border-2",
                   result.final_signal === 'BUY' ? 'border-accent text-accent bg-accent/5' : 
                   result.final_signal === 'SELL' ? 'border-red-500 text-red-500 bg-red-500/5' : 
                   'border-gray-500 text-gray-500 bg-white/5'
                 )}>
                   {result.final_signal === 'BUY' ? <TrendingUp size={48} /> : 
                    result.final_signal === 'SELL' ? <TrendingDown size={48} /> : 
                    <Minus size={48} />}
                 </div>
                 <div>
                    <h2 className="text-sm font-mono text-gray-500 uppercase tracking-[0.2em] mb-1">Ensemble Decision</h2>
                    <div className="flex items-baseline gap-3">
                      <span className={cn(
                        "text-7xl font-bold tracking-tighter",
                        result.final_signal === 'BUY' ? 'text-accent' : 
                        result.final_signal === 'SELL' ? 'text-red-500' : 'text-gray-400'
                      )}>
                        {result.final_signal}
                      </span>
                      <span className="text-3xl font-mono font-bold text-white/20">@{(result.confidence || 0).toFixed(1)}%</span>
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
                   <span className="text-[10px] font-mono text-gray-500">WEIGHT: 40%</span>
                </div>
                <div className="h-[200px] w-full" style={{ minHeight: 200, minWidth: 0 }}>
                  {historyData && historyData.length > 0 && (
                    <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={200}>
                      <LineChart data={historyData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                        <XAxis dataKey="label" hide />
                        <YAxis domain={['auto', 'auto']} hide />
                        <Tooltip 
                          contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                          itemStyle={{ fontSize: '12px' }}
                        />
                        <Line type="monotone" dataKey="price" stroke="rgba(255,255,255,0.3)" strokeWidth={2} dot={false} />
                        <Line type="monotone" dataKey="price" data={historyData.filter(d => d.isPrediction)} stroke="#00d4ff" strokeWidth={2} strokeDasharray="5 5" dot={false} activeDot={{ r: 6, fill: '#fff', stroke: '#00d4ff', strokeWidth: 2 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  )}
                </div>
                <div className="p-3 rounded-lg bg-white/5 border border-white/5">
                  <p className="text-xs text-gray-400 leading-relaxed italic">
                    Forecast Price: ${(result.signal_breakdown?.lstm?.predicted_price || 0).toFixed(2)} 
                    ({((result.signal_breakdown?.lstm?.expected_return || 0) * 100).toFixed(2)}%)
                  </p>
                </div>
              </div>

              {/* XGBOOST MODULE */}
              <div className="glass-panel p-6 rounded-2xl flex flex-col gap-4 bg-[#0d0d14]">
                 <div className="flex justify-between items-center">
                   <h3 className="font-bold text-sm flex items-center gap-2"><Activity size={16} className="text-purple-500" /> Model Conviction</h3>
                   <span className="text-[10px] font-mono text-gray-500">WEIGHT: 35%</span>
                </div>
                <div className="h-[200px] w-full" style={{ minHeight: 200, minWidth: 0 }}>
                   {result.signal_breakdown && (
                     <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={200}>
                        <BarChart data={[
                          { name: 'LSTM', val: Math.abs(result.signal_breakdown?.model_scores?.lstm_expected_return_pct || 0) },
                          { name: 'XGB', val: (result.signal_breakdown?.model_scores?.xgboost_confidence_pct || 0) },
                          { name: 'NLP', val: Math.abs((result.signal_breakdown?.model_scores?.sentiment_score || 0) * 100) }
                        ]} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                          <XAxis dataKey="name" stroke="rgba(255,255,255,0.5)" fontSize={10} />
                          <YAxis hide />
                          <Tooltip contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }} />
                          <Bar dataKey="val" fill="#7c3aed" radius={[4, 4, 0, 0]} barSize={40} />
                        </BarChart>
                     </ResponsiveContainer>
                   )}
                </div>
                <div className="p-3 rounded-lg bg-white/5 border border-white/5">
                  <p className="text-xs text-gray-400 leading-relaxed italic">
                    Trend Prediction: {result.signal_breakdown?.xgboost?.trend || "NEUTRAL"} 
                    ({((result.signal_breakdown?.xgboost?.confidence || 0) * 100).toFixed(1)}% confidence)
                  </p>
                </div>
              </div>

              {/* SENTIMENT MODULE */}
              <div className="glass-panel p-6 rounded-2xl flex flex-col gap-4 bg-[#0d0d14]">
                 <div className="flex justify-between items-center">
                   <h3 className="font-bold text-sm flex items-center gap-2"><Newspaper size={16} className="text-blue-500" /> NLP Sentiment Score</h3>
                   <span className="text-[10px] font-mono text-gray-500">WEIGHT: 25%</span>
                </div>
                <div className="h-24 flex flex-col justify-center gap-4">
                   <div className="h-3 w-full bg-white/5 rounded-full overflow-hidden flex relative">
                      <div className="absolute top-0 bottom-0 left-1/2 w-[2px] bg-white/20 z-10" />
                      {(result.signal_breakdown?.sentiment?.score || 0) < 0 ? (
                        <div 
                          className="h-full bg-red-500 transition-all ml-auto" 
                          style={{ width: `${Math.abs(result.signal_breakdown?.sentiment?.score || 0) * 50}%`, marginRight: '50%' }} 
                        />
                      ) : (
                        <div 
                          className="h-full bg-green-500 transition-all" 
                          style={{ width: `${(result.signal_breakdown?.sentiment?.score || 0) * 50}%`, marginLeft: '50%' }} 
                        />
                      )}
                   </div>
                   <div className="flex justify-between text-[10px] text-gray-500 font-mono">
                      <span>BEARISH (-1.0)</span>
                      <span className="text-white font-bold text-sm">{(result.signal_breakdown?.sentiment?.score || 0).toFixed(2)}</span>
                      <span>BULLISH (+1.0)</span>
                   </div>
                </div>
                <div className="space-y-2 max-h-[150px] overflow-auto pr-2">
                   {(result.signal_breakdown?.sentiment?.recent_headlines || []).map((h: any, i: number) => (
                     <div key={i} className="p-2 rounded bg-white/5 border border-white/5 flex justify-between gap-4 items-start">
                        <span className="text-[11px] text-gray-400 line-clamp-1">{h.title}</span>
                        <span className={cn(
                          "text-[9px] font-bold px-1.5 py-0.5 rounded",
                          h.sentiment > 0 ? "text-green-500 bg-green-500/10" : "text-red-500 bg-red-500/10"
                        )}>{(h.sentiment || 0).toFixed(2)}</span>
                     </div>
                   ))}
                </div>
              </div>

              {/* RISK ASSESSMENT */}
              <div className="glass-panel p-6 rounded-2xl flex flex-col gap-4 bg-[#0d0d14]">
                 <h3 className="font-bold text-sm flex items-center gap-2"><ShieldAlert size={16} className="text-amber-500" /> Strategic Execution</h3>
                 <div className="grid grid-cols-2 gap-4 flex-1">
                    <div className="p-4 rounded-xl bg-surface border border-white/5">
                       <p className="text-[10px] text-gray-500 uppercase font-bold mb-1 tracking-widest">Stop Loss</p>
                       <p className="text-2xl font-mono font-bold text-red-500">-{(result.risk_assessment?.suggested_stop_loss_pct || 0).toFixed(1)}%</p>
                    </div>
                    <div className="p-4 rounded-xl bg-surface border border-white/5">
                       <p className="text-[10px] text-gray-500 uppercase font-bold mb-1 tracking-widest">R:R Ratio</p>
                       <p className="text-2xl font-mono font-bold text-white">{(result.risk_assessment?.risk_reward_ratio || 0).toFixed(2)}</p>
                    </div>
                    <div className="col-span-2 p-4 rounded-xl bg-accent/5 border border-accent/10">
                       <p className="text-xs text-gray-400 italic">&quot;Model suggests a {result.risk_assessment?.volatility || "normal"} volatility regime with {(result.risk_assessment?.suggested_position_size_pct || 0).toFixed(1)}% capital allocation and {(result.risk_assessment?.reward_target_pct || 0).toFixed(1)}% reward target.&quot;</p>
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
