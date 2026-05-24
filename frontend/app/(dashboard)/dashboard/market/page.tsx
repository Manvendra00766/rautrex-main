"use client";

import { useState, useEffect, useRef } from "react";
import { CardSurface } from "@/components/ui/CardSurface";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { MetricCard } from "@/components/ui/MetricCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { createChart, ColorType, CandlestickSeries, LineSeries, HistogramSeries } from 'lightweight-charts';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import { motion, AnimatePresence } from "framer-motion";
import { Activity, Star, BarChart2, ChevronUp, ChevronDown, Info, BookOpen, GripVertical, X, TrendingUp } from "lucide-react";
import { ChartSkeleton } from "@/components/ui/ChartSkeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { TickerChip } from "@/components/ui/TickerChip";
import { useToast } from "@/components/ui/Toast";
import { useIsMobile } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { apiFetch, apiFetchWithRetry } from "@/lib/api";

import { useMarketStore } from "@/lib/market-store";

export default function MarketHub() {
  const { activeTicker: ticker, setActiveTicker: setTicker } = useMarketStore();
  const isMobile = useIsMobile();
  const [configExpanded, setConfigExpanded] = useState(true);

  // Data states
  const [quote, setQuote] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [fundamentals, setFundamentals] = useState<any>(null);
  const [news, setNews] = useState<any[]>([]);
  const [info, setInfo] = useState<any>(null);
  
  const [indices, setIndices] = useState<any[]>([]);
  const [movers, setMovers] = useState<any>({ gainers: [], losers: [], active: [] });
  const [screener, setScreener] = useState<any[]>([]);

  const [period, setPeriod] = useState("1mo");
  const [chartType, setChartType] = useState<"candlestick" | "line">("candlestick");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const { toast } = useToast();
  
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);

  // Initial Load
  useEffect(() => {
    const saved = localStorage.getItem("rautrex_watchlist");
    if (saved) setWatchlist(JSON.parse(saved));
    else setWatchlist(["AAPL", "MSFT", "NVDA", "BTC-USD"]);
    
    fetchIndices();
    fetchMovers();
    fetchScreener();

    if (isMobile) setConfigExpanded(false);
  }, [isMobile]);

  /**
   * Fetches all market data for the selected ticker.
   * Uses Promise.allSettled so one failing endpoint doesn't cascade.
   * Historical data uses exponential backoff retry (3 attempts).
   */
  const fetchData = async () => {
    if (!ticker) return;
    setLoading(true);
    setError(null);
    setHistoryError(null);
    if (isMobile) setConfigExpanded(false);
    
    // Fetch each endpoint independently so one failure doesn't cascade
    const results = await Promise.allSettled([
      apiFetchWithRetry(`/stocks/${ticker}/quote`, {}, 3),
      apiFetchWithRetry(`/stocks/${ticker}/history?period=${period}`, {}, 3),
      apiFetchWithRetry(`/stocks/${ticker}/fundamentals`, {}, 3),
      apiFetchWithRetry(`/stocks/${ticker}/news`, {}, 2),
      apiFetchWithRetry(`/stocks/${ticker}/info`, {}, 2),
    ]);

    // Process quote
    if (results[0].status === 'fulfilled') {
      setQuote(results[0].value ?? null);
    } else {
      console.error(`[Market] Quote fetch failed for ${ticker}:`, results[0].reason?.message);
      setQuote(null);
    }

    // Process historical data (critical for chart)
    if (results[1].status === 'fulfilled') {
      const hData = results[1].value;
      const historyArray = (hData?.data ?? []).filter(Boolean);
      setHistory(historyArray);
      if (historyArray.length === 0) {
        console.warn(`[Market] History endpoint returned empty data array for ${ticker} (period=${period})`);
        setHistoryError(`API returned empty data for ${ticker}`);
      }
    } else {
      const errMsg = results[1].reason?.message || 'Unknown error';
      console.error(`[Market] History fetch failed for ${ticker} (period=${period}):`, errMsg);
      setHistoryError(`Chart data failed: ${errMsg}`);
      setHistory([]);
    }

    // Process fundamentals
    if (results[2].status === 'fulfilled') {
      setFundamentals(results[2].value ?? null);
    } else {
      console.error(`[Market] Fundamentals fetch failed for ${ticker}:`, results[2].reason?.message);
      setFundamentals(null);
    }

    // Process news
    if (results[3].status === 'fulfilled') {
      setNews((results[3].value?.news ?? []).filter(Boolean));
    } else {
      console.error(`[Market] News fetch failed for ${ticker}:`, results[3].reason?.message);
      setNews([]);
    }

    // Process info
    if (results[4].status === 'fulfilled') {
      setInfo(results[4].value ?? null);
    } else {
      console.error(`[Market] Info fetch failed for ${ticker}:`, results[4].reason?.message);
      setInfo(null);
    }

    // Check if all critical endpoints failed (likely auth issue)
    const allFailed = results.every(r => r.status === 'rejected');
    if (allFailed) {
      setError("Failed to fetch market data. Please check your connection or try signing in again.");
      toast({ type: 'error', title: 'Fetch Error', description: 'All market data requests failed.' });
    } else {
      toast({ type: 'success', title: 'Data Updated', description: `Market profile for ${ticker} refreshed.` });
    }

    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, [ticker, period]);

  // Handle Chart
  useEffect(() => {
    if (!chartContainerRef.current || !history.length) return;
    if (chartRef.current) chartRef.current.remove();

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: 'var(--text-secondary)',
        fontFamily: 'Inter'
      },
      grid: {
        vertLines: { color: 'var(--border)' },
        horzLines: { color: 'var(--border)' },
      },
      width: chartContainerRef.current.clientWidth,
      height: isMobile ? 300 : 450,
      timeScale: { timeVisible: true, secondsVisible: false }
    });

    if (chartType === 'candlestick') {
      const candleSeries = chart.addSeries(CandlestickSeries, {
        upColor: 'var(--positive)', downColor: 'var(--negative)', borderVisible: false,
        wickUpColor: 'var(--positive)', wickDownColor: 'var(--negative)',
      });
      candleSeries.setData(history);
    } else {
      const lineSeries = chart.addSeries(LineSeries, {
        color: 'var(--accent-teal)', lineWidth: 2,
      });
      lineSeries.setData(history.filter(Boolean).map(d => ({ time: d.time, value: d.close })));
    }

    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: 'var(--border-strong)',
      priceFormat: { type: 'volume' },
      priceScaleId: '',
    });
    volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    volumeSeries.setData(history.filter(Boolean).map(d => ({
      time: d.time,
      value: d.volume,
      color: d.close > d.open ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'
    })));

    chartRef.current = chart;
    const handleResize = () => chart.applyOptions({ width: chartContainerRef.current?.clientWidth || 0 });
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [history, chartType, isMobile]);

  const fetchIndices = async () => apiFetch("/market/indices").then(data => setIndices(data?.indices ?? [])).catch(console.error);
  const fetchMovers = async () => apiFetch("/market/movers").then(data => setMovers(data ?? { gainers: [], losers: [], active: [] })).catch(console.error);
  const fetchScreener = async () => apiFetch("/market/screener").then(data => setScreener(data?.results ?? [])).catch(console.error);

  const toggleWatchlist = (t: string) => {
    let nl = [...watchlist];
    if (nl.includes(t)) nl = nl.filter(x => x !== t);
    else nl.push(t);
    setWatchlist(nl);
    localStorage.setItem("rautrex_watchlist", JSON.stringify(nl));
    toast({ type: 'info', title: nl.includes(t) ? 'Added to Watchlist' : 'Removed from Watchlist', description: `${t} updated.` });
  };

  const onDragEnd = (result: any) => {
    if (!result.destination) return;
    const items = Array.from(watchlist);
    const [reorderedItem] = items.splice(result.source.index, 1);
    items.splice(result.destination.index, 0, reorderedItem);
    setWatchlist(items);
    localStorage.setItem("rautrex_watchlist", JSON.stringify(items));
  };

  return (
    <div className="flex flex-col gap-6 max-w-[1600px] mx-auto w-full pb-12">
      
      {/* TOP: Page title & actions */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="flex flex-col gap-2">
          <h1 className="text-xl md:text-2xl font-bold text-text-primary flex items-center gap-2">
            <Activity size={24} className="text-accent" /> Market Hub
          </h1>
          {quote && <TickerChip ticker={ticker} price={quote.price} change={quote.change_percent} onClear={() => setTicker("")} />}
        </div>
        <div className="flex items-center gap-2 w-full md:w-auto">
          <Button onClick={() => toggleWatchlist(ticker)} variant="outline" className="flex-1 md:flex-none bg-card border-border gap-2 text-xs h-10">
            <Star size={14} className={watchlist.includes(ticker) ? "fill-amber-400 text-amber-400" : ""} /> Watchlist
          </Button>
          <Button onClick={fetchData} loading={loading} className="flex-1 md:flex-none bg-accent hover:bg-accent/90 text-text-primary font-bold gap-2 px-6 h-10">
            REFRESH
          </Button>
        </div>
      </div>

      {/* INDICES TAPE */}
      <div className="flex md:grid md:grid-cols-4 lg:grid-cols-8 gap-3 overflow-x-auto pb-2 md:pb-0 no-scrollbar custom-scrollbar">
        {(indices ?? []).filter(Boolean).map(idx => (
          <CardSurface key={idx.name} className="p-3 flex flex-col gap-1 cursor-pointer hover:bg-card/50 transition-colors min-w-[120px] md:min-w-0" onClick={() => setTicker(idx.ticker)}>
            <span className="text-[9px] text-text-muted font-bold uppercase tracking-widest truncate">{idx.name}</span>
            <div className="flex justify-between items-end">
              <span className="font-mono font-bold text-xs text-text-primary">{(idx.value || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
              <span className={`font-mono text-[9px] font-bold ${(idx.change_percent || 0) > 0 ? 'text-positive' : 'text-negative'}`}>
                {(idx.change_percent || 0) > 0 ? '+' : ''}{(idx.change_percent || 0).toFixed(2)}%
              </span>
            </div>
          </CardSurface>
        ))}
      </div>

      {/* CHART CONFIG */}
      <CardSurface className="overflow-hidden">
        <button 
          onClick={() => setConfigExpanded(!configExpanded)}
          className="w-full flex items-center justify-between p-4 hover:bg-card/50 transition-colors border-b border-border"
        >
          <SectionHeader 
            title="Chart Config & Period" 
            icon={<BarChart2 size={16} />}
            className="text-[10px] md:text-sm tracking-widest"
          />
          {configExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
        <AnimatePresence>
          {configExpanded && (
            <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden">
              <div className="p-4 md:p-6 flex flex-col md:flex-row flex-wrap gap-6 md:gap-8 items-start md:items-end">
                 <div className="space-y-2 w-full md:w-auto">
                   <p className="text-[10px] text-text-muted uppercase font-bold tracking-widest">Time Period</p>
                   <div className="flex flex-wrap gap-1 p-1 bg-card rounded-lg border border-border overflow-x-auto no-scrollbar">
                        {["1d","5d","1mo","3mo","6mo","1y","5y","max"].map(p => (
                          <button 
                            key={p} 
                            onClick={() => setPeriod(p)}
                            className={cn("px-3 py-1.5 text-[10px] font-bold rounded-md transition-all whitespace-nowrap", period === p ? 'bg-accent text-text-primary' : 'text-text-muted hover:text-text-primary')}
                          >
                            {p.toUpperCase()}
                          </button>
                        ))}
                   </div>
                 </div>
                 <div className="space-y-2 w-full md:w-auto">
                    <p className="text-[10px] text-text-muted uppercase font-bold tracking-widest">Rendering Mode</p>
                    <div className="flex gap-1 p-1 bg-card rounded-lg border border-border w-fit">
                      <button onClick={() => setChartType("line")} className={cn("px-4 py-1.5 text-[10px] font-bold rounded-md transition-all", chartType === 'line' ? 'bg-accent text-text-primary' : 'text-text-muted hover:text-text-primary')}>LINE</button>
                      <button onClick={() => setChartType("candlestick")} className={cn("px-4 py-1.5 text-[10px] font-bold rounded-md transition-all", chartType === 'candlestick' ? 'bg-accent text-text-primary' : 'text-text-muted hover:text-text-primary')}>CANDLES</button>
                    </div>
                 </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </CardSurface>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[500px]">
        {/* LEFT */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          {loading ? <ChartSkeleton type="line" className="h-[300px] md:h-[450px]" /> : error ? <ErrorState onRetry={fetchData} message={error} /> : !history || history.length === 0 ? (
            <CardSurface className="h-[300px] md:h-[450px] flex flex-col items-center justify-center text-text-muted font-mono text-xs italic gap-2">
              <span>No historical data available for {ticker}</span>
              {historyError && (
                <span className="text-red-400 text-[10px] max-w-md text-center">
                  Debug: {historyError}
                </span>
              )}
              <Button onClick={fetchData} variant="outline" className="mt-2 text-[10px] h-7">
                Retry
              </Button>
            </CardSurface>
          ) : (
            <CardSurface className="p-2 md:p-4" style={{ width: '100%', minWidth: 0 }}>
               <div ref={chartContainerRef} className="w-full h-[300px] md:h-[450px]" style={{ minWidth: 0 }} />
            </CardSurface>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
             <CardSurface className="p-6 flex flex-col gap-4">
                <SectionHeader 
                    title="Fundamentals" 
                    icon={<Info size={14} className="text-accent"/>}
                    className="text-[10px] tracking-[0.2em] border-b border-border pb-3"
                />
                {fundamentals ? (
                  <div className="grid grid-cols-2 gap-x-8 gap-y-4 font-mono text-[11px]">
                    <div className="flex justify-between border-b border-border pb-1"><span className="text-text-muted italic">Mkt Cap</span><span className="text-text-primary">{((quote?.market_cap || 0) / 1e9).toFixed(2)}B</span></div>
                    <div className="flex justify-between border-b border-border pb-1"><span className="text-text-muted italic">P/E</span><span className="text-text-primary">{(fundamentals.pe_ratio || 0).toFixed(1)}</span></div>
                    <div className="flex justify-between border-b border-border pb-1"><span className="text-text-muted italic">EPS</span><span className="text-text-primary">${(fundamentals.eps || 0).toFixed(2)}</span></div>
                    <div className="flex justify-between border-b border-border pb-1"><span className="text-text-muted italic">Yield</span><span className="text-text-primary">{((fundamentals.dividend_yield || 0) * 100).toFixed(2)}%</span></div>
                    <div className="flex justify-between border-b border-border pb-1"><span className="text-text-muted italic">ROE</span><span className="text-text-primary">{((fundamentals.roe || 0) * 100).toFixed(1)}%</span></div>
                    <div className="flex justify-between border-b border-border pb-1"><span className="text-text-muted italic">P/B</span><span className="text-text-primary">{(fundamentals.pb_ratio || 0).toFixed(1)}</span></div>
                  </div>
                ) : <div className="h-24 animate-pulse bg-muted/50 rounded-lg" />}
             </CardSurface>

             <CardSurface className="p-6 flex flex-col gap-4 h-[350px]">
                <SectionHeader 
                    title="Intelligence" 
                    icon={<BookOpen size={14} className="text-accent"/>}
                    className="text-[10px] tracking-[0.2em] border-b border-border pb-3"
                />
                <div className="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
                   {(news ?? []).filter(Boolean).map((n, i) => (
                     <a key={i} href={n.link} target="_blank" rel="noreferrer" className="block p-3 rounded-xl bg-card hover:bg-card/50 border border-border transition-all group">
                        <p className="text-[10px] text-text-primary font-bold mb-2 line-clamp-2 group-hover:text-accent transition-colors">{n.title}</p>
                        <div className="flex justify-between text-[9px] text-text-muted font-mono">
                           <span className="uppercase">{n.publisher}</span>
                           <span>{new Date((n.time || 0) * 1000).toLocaleDateString()}</span>
                        </div>
                     </a>
                   ))}
                </div>
             </CardSurface>
          </div>
        </div>

        {/* RIGHT */}
        <div className="lg:col-span-4 flex flex-col gap-6">
           <CardSurface className="p-4 flex flex-col min-h-[300px]">
              <SectionHeader 
                title="Personal Watchlist" 
                icon={<Star size={14} className="text-amber-500 fill-amber-500"/>}
                className="text-[10px] tracking-[0.2em] mb-4"
              />
              <DragDropContext onDragEnd={onDragEnd}>
                <Droppable droppableId="watchlist">
                  {(provided) => (
                    <div {...provided.droppableProps} ref={provided.innerRef} className="flex-1 overflow-y-auto space-y-1 custom-scrollbar pr-1">
                      {(watchlist ?? []).filter(Boolean).map((t, index) => (
                        <Draggable key={t} draggableId={t} index={index}>
                          {(provided, snapshot) => (
                            <div ref={provided.innerRef} {...provided.draggableProps} className={cn("flex items-center justify-between p-2.5 rounded-xl bg-card border hover:border-border-strong transition-all group", snapshot.isDragging ? 'border-accent shadow-2xl z-50 scale-105' : 'border-border')}>
                              <div className="flex items-center gap-3">
                                <div {...provided.dragHandleProps} className="text-text-muted hover:text-text-primary cursor-grab"><GripVertical size={14}/></div>
                                <span className="font-mono font-bold text-xs text-text-primary cursor-pointer group-hover:text-accent" onClick={() => setTicker(t)}>{t}</span>
                              </div>
                              <button onClick={() => toggleWatchlist(t)} className="text-text-muted hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"><X size={14}/></button>
                            </div>
                          )}
                        </Draggable>
                      ))}
                      {provided.placeholder}
                    </div>
                  )}
                </Droppable>
              </DragDropContext>
           </CardSurface>

           <CardSurface className="p-4 flex flex-col h-auto">
              <SectionHeader 
                title="Market Movers" 
                icon={<TrendingUp size={14} className="text-accent" />}
                className="text-[10px] tracking-[0.2em] mb-4"
              />
              <Tabs defaultValue="gainers" className="w-full flex-1 flex flex-col">
                <TabsList className="grid grid-cols-3 bg-card border border-border h-8 mb-4">
                  <TabsTrigger value="gainers" className="text-[9px] font-bold">GAINERS</TabsTrigger>
                  <TabsTrigger value="losers" className="text-[9px] font-bold">LOSERS</TabsTrigger>
                  <TabsTrigger value="active" className="text-[9px] font-bold">VOLUME</TabsTrigger>
                </TabsList>
                {['gainers', 'losers', 'active'].map(type => (
                  <TabsContent key={type} value={type} className="flex-1 overflow-auto custom-scrollbar mt-0">
                     {(movers?.[type] ?? []).filter(Boolean).map((m: any) => (
                        <div key={m.ticker} onClick={() => setTicker(m.ticker)} className="flex justify-between items-center p-2.5 rounded-xl hover:bg-card/50 cursor-pointer font-mono text-[11px] group border border-transparent hover:border-border transition-all mb-1">
                          <span className="font-black text-text-primary group-hover:text-accent transition-colors">{m.ticker}</span>
                          <div className="text-right">
                             <p className="text-text-primary">${(m.price || 0).toFixed(2)}</p>
                             <p className={cn("font-bold text-[10px]", (m.change_percent || 0) > 0 ? "text-positive" : "text-negative")}>
                               {(m.change_percent || 0) > 0 ? '+' : ''}{(m.change_percent || 0).toFixed(2)}%
                             </p>
                          </div>
                        </div>
                     ))}
                  </TabsContent>
                ))}
              </Tabs>
           </CardSurface>
        </div>
      </div>
    </div>
  );
}
