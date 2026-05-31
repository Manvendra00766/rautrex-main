"use client"

import React, { useEffect, useState } from 'react'
import { useDCFStore } from '@/store/dcfStore'
import { DCFInput } from '@/types/dcf'
import { CardSurface } from "@/components/ui/CardSurface"
import { SectionHeader } from "@/components/ui/SectionHeader"
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { Badge } from '@/components/ui/badge'
import { Tooltip } from '@/components/ui/tooltip'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { useToast } from '@/components/ui/Toast'
import PresetSelector from './PresetSelector'
import CompareMode from './CompareMode'
import { 
  Plus, Minus, Loader2, Save, Trash2, TrendingUp, TrendingDown, 
  Info, ChevronDown, ChevronUp, History, Calculator, Share2, Globe, Check, ArrowRightLeft,
  ChevronRight, Download, AlertTriangle
} from 'lucide-react'
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, 
  ResponsiveContainer, Cell, LabelList, Legend
} from 'recharts'
import { formatError } from '@/lib/utils'
import ChartWrapper from '@/components/ChartWrapper';
import { getAuthHeaders } from '@/lib/api';

export default function DCFCalculator() {
  const { 
    inputs, result, history, isCalculating, isSaving,
    setInputs, calculate, saveValuation, fetchHistory, deleteValuation, toggleShare 
  } = useDCFStore();
  
  const { toast } = useToast();
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isCompareMode, setIsCompareMode] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isFetching, setIsFetching] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Derived state for Currency & Localization
  const isIndian = result ? result.currency === 'INR' : (inputs.ticker?.endsWith('.NS') || inputs.ticker?.endsWith('.BO'));
  const currencySymbol = result ? (result.currency === 'INR' ? '₹' : '$') : (isIndian ? '₹' : '$');
  const unit = result ? result.unit : (isIndian ? 'Cr' : 'Mn');
  const unitLabel = result ? result.unit_label : (isIndian ? '₹ Cr' : '$ Mn');
  const locale = result ? (result.currency === 'INR' ? 'en-IN' : 'en-US') : (isIndian ? 'en-IN' : 'en-US');
  const currencyCode = result ? result.currency : (isIndian ? 'INR' : 'USD');

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: currencyCode,
      maximumFractionDigits: 2
    }).format(val) + ` ${unit}`;
  };

  const formatPrice = (val: number) => {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: currencyCode,
      maximumFractionDigits: 2
    }).format(val);
  };

  // Chart Data Preparation
  const chartData = result ? [
    ...result.projected_fcfs.map((fcf, i) => ({ 
      name: `Year ${i+1}`, 
      fcf: fcf,
      terminal: 0,
      isTerminal: false 
    })),
    { 
      name: 'Terminal', 
      fcf: 0, 
      terminal: result.terminal_value,
      isTerminal: true 
    }
  ] : [];

  const maxFCF = result ? Math.max(...result.projected_fcfs) : 0;
  const isLogScale = result && result.terminal_value > 10 * maxFCF && maxFCF > 0;

  // Margin of Safety Zones
  const buyZones = result ? [
    { label: 'Strong Buy', price: result.intrinsic_value_per_share * 0.60, color: 'bg-green-500/20 text-green-500 border-green-500/30' },
    { label: 'Buy', price: result.intrinsic_value_per_share * 0.75, color: 'bg-teal-500/20 text-teal-500 border-teal-500/30' },
    { label: 'Fair Value', price: result.intrinsic_value_per_share * 1.0, color: 'bg-gray-500/20 text-gray-400 border-gray-500/30' },
  ] : [];

  const currentPrice = result?.current_market_price || 0;
  const activeZone = buyZones.find(z => currentPrice <= z.price);

  // Debounced Ticker Search for Financials
  useEffect(() => {
    if (!inputs.ticker || inputs.ticker.length < 2) return;
    
    const handler = setTimeout(async () => {
      // Don't auto-fetch if it looks like we already have data for this ticker 
      // (simple heuristic: if revenue is non-zero)
      if (inputs.revenue.some(r => r > 0)) return;

      setIsFetching(true);
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/stocks/${inputs.ticker.toUpperCase()}`);
        if (!response.ok) throw new Error('Ticker not found');
        
        const data = await response.json();
        
        // Auto-fill form
        setInputs({
          ...inputs,
          revenue: data.revenue.length > 0 ? data.revenue : inputs.revenue,
          ebit_margin: data.ebit_margin || inputs.ebit_margin,
          tax_rate: data.tax_rate || inputs.tax_rate,
          capex_pct: data.capex_pct || inputs.capex_pct,
          da_pct: data.da_pct || inputs.da_pct || 0.03,
          nwc_change_pct: data.nwc_change_pct || inputs.nwc_change_pct,
          shares_outstanding: data.shares_outstanding || inputs.shares_outstanding,
          net_debt: data.net_debt || inputs.net_debt,
          currency: data.currency,
          unit: data.unit,
          unit_label: data.unit_label,
          exchange: data.exchange,
          warnings: data.warnings || [],
          field_sources: data.field_sources || {}
        });

        toast({ 
          type: 'success', 
          title: 'Data Loaded', 
          description: `Automatically populated financials for ${data.company_name}` 
        });
      } catch (error) {
        toast({ 
          type: 'info', 
          title: 'Manual Entry Required', 
          description: 'Could not fetch automated data for this ticker. Please enter details manually.' 
        });
      } finally {
        setIsFetching(false);
      }
    }, 800); // 800ms debounce to avoid spamming while typing NSE tickers like RELIANCE.NS

    return () => clearTimeout(handler);
  }, [inputs.ticker]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleRevenueChange = (index: number, value: string) => {
    const newRevenue = [...inputs.revenue];
    newRevenue[index] = parseFloat(Number(value).toFixed(2)) || 0;
    setInputs({ ...inputs, revenue: newRevenue });
  };

  const addRevenueYear = () => {
    if (inputs.revenue.length >= 10) return;
    setInputs({ ...inputs, revenue: [...inputs.revenue, 0] });
  };

  const removeRevenueYear = () => {
    if (inputs.revenue.length <= 2) return;
    setInputs({ ...inputs, revenue: inputs.revenue.slice(0, -1) });
  };

  const handleApplyPreset = (values: Partial<DCFInput>) => {
    setInputs({ ...inputs, ...values });
    toast({ type: 'info', title: 'Preset Applied', description: 'Assumptions updated successfully.' });
  };

  const handleCalculate = async () => {
    if (!inputs.ticker) {
      toast({ type: 'error', title: 'Ticker Required', description: 'Please enter a stock ticker' });
      return;
    }

    // Validation: WACC vs TGR
    if (inputs.wacc <= inputs.terminal_growth_rate) {
      toast({ 
        type: 'error', 
        title: 'Validation Error', 
        description: 'WACC must be greater than Terminal Growth Rate' 
      });
      return;
    }

    try {
      await calculate();
      toast({ type: 'success', title: 'Calculation Complete', description: `Valuation for ${inputs.ticker} updated` });
    } catch (error: any) {
      toast({ type: 'error', title: 'Calculation Failed', description: formatError(error) });
    }
  };

  const handleSave = async () => {
    try {
      await saveValuation();
      toast({ type: 'success', title: 'Valuation Saved', description: 'Record added to history' });
    } catch (error: any) {
      toast({ type: 'error', title: 'Save Failed', description: error.message });
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this valuation?')) return;
    try {
      await deleteValuation(id);
      toast({ type: 'success', title: 'Valuation Deleted' });
    } catch (error: any) {
      toast({ type: 'error', title: 'Delete Failed', description: error.message });
    }
  };

  const handleShare = async (id: string, is_public: boolean) => {
    try {
      await toggleShare(id, !is_public);
      const action = !is_public ? 'Shared' : 'Private';
      toast({ type: 'success', title: `Valuation is now ${action}` });
    } catch (error: any) {
      toast({ type: 'error', title: 'Share failed', description: error.message });
    }
  };

  const handleExportPDF = async () => {
    if (!result) return;
    try {
      toast({ type: 'info', title: 'Generating Report...', description: 'Please wait while we prepare your PDF.' });
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/dcf/export-pdf`, {
        method: 'POST',
        headers: await getAuthHeaders(),
        body: JSON.stringify(inputs)
      });
      
      if (!response.ok) throw new Error('Failed to initiate export');
      
      const { download_url } = await response.json();
      
      // Fetch the actual PDF blob
      const pdfResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${download_url.replace('/api/v1', '')}`, {
        headers: await getAuthHeaders()
      });
      
      if (!pdfResponse.ok) throw new Error('Failed to download report');
      
      const blob = await pdfResponse.blob();
      console.log('PDF Blob received:', { size: blob.size, type: blob.type });
      
      if (blob.size < 1000) {
        console.error('Blob is suspiciously small, might be an error message or corrupted.');
      }
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `DCF_Report_${inputs.ticker}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => window.URL.revokeObjectURL(url), 5000);

      toast({ type: 'success', title: 'Report Downloaded' });
    } catch (error: any) {
      toast({ type: 'error', title: 'Export Failed', description: error.message });
    }
  };

  const copyShareLink = (id: string) => {
    const url = `${window.location.origin}/share/${id}`;
    navigator.clipboard.writeText(url);
    setCopiedId(id);
    toast({ type: 'info', title: 'Link Copied', description: 'Anyone with this link can view the valuation.' });
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="flex flex-col gap-8 pb-20">
      <div className="mb-8">
        <h1 className="text-3xl font-black text-text-primary tracking-tight uppercase">DCF VALUATION</h1>
        <p className="text-text-muted mt-1 font-medium">
          Estimate intrinsic value of global equities with professional quantitative models
        </p>
      </div>

      {/* Compare Mode Call to Action */}
      {!isCompareMode && (
        <CardSurface 
          className="group cursor-pointer border-dashed border-border hover:border-accent/50 bg-elevated/20 hover:bg-elevated/40 transition-all p-6 mb-4 shadow-none"
          onClick={() => setIsCompareMode(true)}
        >
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex-1">
              <SectionHeader 
                title="Which stock is more undervalued?"
                description="Compare two stocks side-by-side to see their relative margin of safety and FCF projections."
                icon={<ArrowRightLeft size={18} />}
                className="mb-0"
              />
            </div>
            
            <div className="flex items-center gap-4 bg-background/40 p-4 rounded-2xl border border-border group-hover:border-accent/20 transition-colors">
              <div className="flex -space-x-3">
                <div className="w-10 h-10 rounded-full bg-accent/20 border border-accent/30 flex items-center justify-center text-xs font-bold text-accent">A</div>
                <div className="w-10 h-10 rounded-full bg-surface border border-border flex items-center justify-center text-xs font-bold text-text-muted">B</div>
              </div>
              <div className="h-4 w-px bg-border" />
              <Button variant="link" className="p-0 text-accent h-auto flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                Enter Compare Mode <ChevronRight size={14} />
              </Button>
            </div>
          </div>
        </CardSurface>
      )}

      {isCompareMode ? (
        <div className="animate-in slide-in-from-top-4 duration-500">
          <div className="flex justify-center mb-8">
            <Button 
              variant="outline" 
              className="rounded-full px-8 border-accent text-accent hover:bg-accent hover:text-text-primary transition-all"
              onClick={() => setIsCompareMode(false)}
            >
              <ArrowRightLeft size={16} className="mr-2" />
              Exit Compare Mode
            </Button>
          </div>
          <CompareMode />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 animate-in fade-in duration-500">
          {/* LEFT PANEL: FORM */}
          <CardSurface className="">
            <SectionHeader 
              title="Valuation Inputs" 
              description="Enter financial parameters for DCF projection" 
              icon={<Calculator size={20} />} 
            />
          <div className="space-y-6">
            {/* PRESET SELECTOR INTEGRATION */}
            <div className="space-y-4">
              <PresetSelector onApply={handleApplyPreset} />
              <div className="h-px bg-border w-full" />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-text-primary">Ticker</Label>
                <div className="relative">
                  <Input 
                    placeholder="e.g. RELIANCE.NS or AAPL" 
                    value={inputs.ticker} 
                    onChange={e => setInputs({ ...inputs, ticker: e.target.value.toUpperCase() })}
                    className="bg-surface border-border pr-10 text-text-primary"
                  />
                  {isFetching && (
                    <div className="absolute right-3 top-1/2 -translate-y-1/2">
                      <Loader2 size={16} className="animate-spin text-accent" />
                    </div>
                  )}
                </div>
              </div>
              <div className="space-y-2">
                <Label className="text-text-primary">Projection Years</Label>
                <div className="flex items-center gap-4 pt-2">
                  <Slider 
                    value={[inputs.projection_years]} 
                    min={1} 
                    max={10} 
                    step={1}
                    onValueChange={v => setInputs({ ...inputs, projection_years: v[0] })}
                    className="flex-1"
                  />
                  <span className="text-sm font-bold w-4 text-text-primary">{inputs.projection_years}</span>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label className="flex items-center gap-2 text-text-primary">
                  Historical Revenue ({unitLabel})
                  <Tooltip content="Last 3-5 years revenue to calculate growth rate">
                    <Info size={14} className="text-text-muted" />
                  </Tooltip>
                </Label>
                <div className="flex gap-2">
                  <Button variant="outline" size="icon" className="h-7 w-7 rounded-full border-border text-text-muted hover:text-text-primary" onClick={removeRevenueYear}>
                    <Minus size={14} />
                  </Button>
                  <Button variant="outline" size="icon" className="h-7 w-7 rounded-full border-border text-text-muted hover:text-text-primary" onClick={addRevenueYear}>
                    <Plus size={14} />
                  </Button>
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {inputs.revenue.map((rev, i) => (
                  <div key={i} className="space-y-1">
                    <span className="text-xs text-text-muted uppercase font-bold">Year {i + 1}</span>
                    <Input 
                      type="number" 
                      step="0.01"
                      value={rev} 
                      onChange={e => handleRevenueChange(i, e.target.value)}
                      className="bg-surface border-border h-8 text-sm text-text-primary"
                    />
                  </div>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {[
                { label: 'EBIT Margin', key: 'ebit_margin', tip: 'Operating profit margin expected' },
                { label: 'Tax Rate', key: 'tax_rate', tip: 'Effective corporate tax rate' },
                { label: 'CapEx % of Rev', key: 'capex_pct', tip: 'Annual capital expenditure as % of revenue' },
                { label: 'ΔNWC % of Rev', key: 'nwc_change_pct', tip: 'Change in net working capital as % of revenue' },
                { label: 'WACC', key: 'wacc', tip: 'Weighted Average Cost of Capital (Discount Rate)' },
                { label: 'Terminal Growth', key: 'terminal_growth_rate', tip: 'Perpetual growth rate after projection period' },
              ].map(field => (
                <div key={field.key} className="space-y-2">
                  <Label className="flex items-center gap-1 text-xs text-text-primary">
                    {field.label} (%)
                    <Tooltip content={field.tip}>
                      <Info size={12} className="text-text-muted" />
                    </Tooltip>
                  </Label>
                  <Input 
                    type="number" 
                    step="0.01"
                    value={parseFloat(Number((inputs as any)[field.key] * 100).toFixed(2))} 
                    onChange={e => setInputs({ ...inputs, [field.key]: parseFloat(Number(parseFloat(e.target.value) / 100).toFixed(4)) })}
                    className="bg-surface border-border text-text-primary"
                  />
                </div>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-xs text-text-primary">Shares Outstanding (Mn)</Label>
                <Input 
                  type="number" 
                  step="0.01"
                  value={inputs.shares_outstanding} 
                  onChange={e => setInputs({ ...inputs, shares_outstanding: parseFloat(Number(e.target.value).toFixed(2)) || 0 })}
                  className="bg-surface border-border text-text-primary"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-xs text-text-primary">Net Debt ({unitLabel})</Label>
                <Input 
                  type="number" 
                  step="0.01"
                  value={inputs.net_debt} 
                  onChange={e => setInputs({ ...inputs, net_debt: parseFloat(Number(e.target.value).toFixed(2)) || 0 })}
                  className="bg-surface border-border text-text-primary"
                />
              </div>
            </div>

            {/* Warnings from extraction layer */}
            {inputs.warnings && inputs.warnings.length > 0 && (
               <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                 <div className="flex items-center gap-2 text-amber-500 text-xs font-bold uppercase mb-2">
                   <AlertTriangle size={14} /> Data Quality Warnings
                 </div>
                 <ul className="list-disc pl-4 text-xs text-amber-500/80 space-y-1 font-medium">
                   {inputs.warnings.map((w, i) => <li key={i}>{w}</li>)}
                 </ul>
               </div>
            )}

            <div className="relative group">
              <div className={`absolute -inset-1 bg-accent/20 rounded-xl blur-lg transition-all duration-1000 group-hover:bg-accent/30 ${result === null || inputs.ticker !== result.ticker ? 'animate-pulse opacity-100' : 'opacity-0'}`} />
              <Button 
                className="relative w-full bg-accent hover:bg-accent/90 text-text-primary font-bold text-[15px] h-14 rounded-lg shadow-xl transition-all active:scale-[0.98]" 
                onClick={handleCalculate}
                disabled={isCalculating}
              >
                {isCalculating ? <Loader2 className="animate-spin mr-2" /> : <Calculator className="mr-2" size={20} />}
                CALCULATE VALUATION
              </Button>
            </div>
          </div>
        </CardSurface>

        {/* RIGHT PANEL: RESULTS */}
        <div className="space-y-8">
          {result ? (
            <>
              <CardSurface className="relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 flex flex-col items-end gap-2">
                  <Badge variant={result.data_quality_score === 'HIGH' ? 'success' : result.data_quality_score === 'MEDIUM' ? 'warning' : 'error'} className="text-xs">
                    Data Quality: {result.data_quality_score}
                  </Badge>
                  {result.upside_downside_pct !== null && (
                    <Badge variant={result.upside_downside_pct > 0 ? 'success' : 'error'} className="text-sm px-3 py-1">
                      {result.upside_downside_pct > 0 ? <TrendingUp size={14} className="mr-1" /> : <TrendingDown size={14} className="mr-1" />}
                      {Math.abs(result.upside_downside_pct * 100).toFixed(1)}% {result.upside_downside_pct > 0 ? 'Upside' : 'Downside'}
                    </Badge>
                  )}
                  {result.projected_fcfs.some(f => f < 0) && (
                    <Badge variant="error" className="text-xs animate-pulse">
                      <AlertTriangle size={10} className="mr-1" /> Negative FCF Detected
                    </Badge>
                  )}
                </div>
                <CardHeader>
                  <CardTitle className="text-text-muted text-sm uppercase tracking-widest font-bold">{result.ticker} Intrinsic Value</CardTitle>
                  <div className="flex flex-col gap-1 mt-2">
                    <span className="text-5xl font-black text-text-primary tracking-tighter">{formatPrice(result.intrinsic_value_per_share)}</span>
                    <span className="text-text-secondary text-sm font-medium">Market Price: {result.current_market_price ? formatPrice(result.current_market_price) : 'N/A'}</span>
                  </div>
                </CardHeader>
                <CardContent>
                  {/* Result Warnings */}
                  {result.warnings && result.warnings.length > 0 && (
                     <div className="mb-4 p-3 bg-negative/10 border border-negative/20 rounded-lg">
                       <div className="flex items-center gap-2 text-negative text-xs font-bold uppercase mb-2">
                         <AlertTriangle size={14} /> Valuation Warnings
                       </div>
                       <ul className="list-disc pl-4 text-xs text-negative/80 space-y-1 font-medium">
                         {result.warnings.map((w, i) => <li key={i}>{w}</li>)}
                       </ul>
                     </div>
                  )}

                  <div className="h-[280px] w-full mt-4 relative" style={{ minHeight: '300px' }}>
                    {/* Negative FCF Zone Annotation */}
                    {result.projected_fcfs.some(f => f < 0) && (
                      <div className="absolute left-10 right-0 bottom-0 top-1/2 bg-negative/5 border-t border-dashed border-negative/20 z-0 flex items-end justify-center pb-2 pointer-events-none">
                        <span className="text-[8px] uppercase font-black text-negative/40 tracking-widest">Negative FCF Zone</span>
                      </div>
                    )}
                    
                    {isMounted ? (
                      <ChartWrapper height={300}>
<ResponsiveContainer width="100%" height="100%" aspect={2}>
                        <BarChart data={chartData} margin={{ top: 20, right: 10, left: 10, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                          <XAxis dataKey="name" stroke="var(--text-text-muted)" fontSize={10} axisLine={false} tickLine={false} />
                          <YAxis 
                            stroke="var(--text-text-muted)" 
                            fontSize={10} 
                            axisLine={false} 
                            tickLine={false} 
                            tickFormatter={v => `${currencySymbol}${v}`}
                            scale={isLogScale ? 'log' : 'auto'}
                            domain={['auto', 'auto']}
                            allowDataOverflow={true}
                          />
                          <RechartsTooltip 
                            contentStyle={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '12px' }}
                            formatter={(value: any, name: string) => [
                              formatCurrency(value), 
                              name === 'fcf' ? 'Free Cash Flow' : 'Terminal Value'
                            ]}
                          />
                          <Legend iconType="circle" wrapperStyle={{ fontSize: '10px', paddingTop: '10px' }} />
                          <Bar dataKey="fcf" name="Projected FCF" fill="var(--accent)" opacity={0.4} radius={[4, 4, 0, 0]}>
                             {chartData.map((entry, index) => (
                               <Cell key={`cell-${index}`} fill={entry.fcf < 0 ? 'var(--negative)' : 'var(--accent)'} fillOpacity={0.4} />
                             ))}
                             <LabelList 
                                dataKey="fcf" 
                                position="top" 
                                formatter={(v: number) => Math.abs(v) > 0 ? Math.round(v) : ''} 
                                style={{ fill: 'var(--text-text-muted)', fontSize: '9px', fontWeight: 'bold' }} 
                              />
                          </Bar>
                          <Bar dataKey="terminal" name="Terminal Value" fill="var(--accent)" radius={[4, 4, 0, 0]}>
                             <LabelList dataKey="terminal" position="top" formatter={(v: number) => v > 0 ? Math.round(v) : ''} style={{ fill: 'var(--accent)', fontSize: '9px', fontWeight: 'bold' }} />
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
</ChartWrapper>
                    ) : (
                      <div className="w-full h-full bg-elevated rounded-2xl animate-pulse" />
                    )}
                  </div>

                  {/* Margin of Safety Zones */}
                  <div className="mt-8 space-y-3">
                    <div className="flex items-center justify-between">
                       <span className="text-xs text-text-muted uppercase font-bold tracking-widest">Margin of Safety</span>
                       {activeZone && (
                         <span className="text-xs text-accent animate-pulse font-bold uppercase tracking-tighter">
                           Target: {activeZone.label}
                         </span>
                       )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {buyZones.map((zone) => {
                        const isCurrentZone = activeZone?.label === zone.label;
                        return (
                          <div 
                            key={zone.label}
                            className={`flex-1 min-w-[100px] p-2 rounded-xl border text-center transition-all ${zone.color} ${isCurrentZone ? 'ring-2 ring-accent ring-offset-2 ring-offset-surface scale-105' : 'opacity-60'}`}
                          >
                            <div className="text-xs uppercase font-black mb-1">{zone.label}</div>
                            <div className="text-xs font-bold">{formatPrice(zone.price)}</div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4 mt-8">
                    {[
                      { label: 'Enterprise Value', value: result.enterprise_value },
                      { label: 'Terminal Value (PV)', value: result.terminal_value },
                      { label: 'Equity Value', value: result.equity_value },
                    ].map(item => (
                      <div key={item.label} className="p-3 rounded-xl bg-elevated/50 border border-border">
                        <span className="text-xs text-text-muted uppercase block mb-1 font-bold">{item.label}</span>
                        <span className="text-sm font-bold text-text-primary font-mono">{formatCurrency(item.value)}</span>
                      </div>
                    ))}
                  </div>

                  <div className="flex flex-col gap-3 mt-6">
                    <Button 
                      className="w-full bg-accent hover:bg-accent/90 text-text-primary font-bold h-11"
                      onClick={handleSave}
                      disabled={isSaving}
                    >
                      {isSaving ? <Loader2 className="animate-spin mr-2" /> : <Save className="mr-2" size={16} />}
                      Save This Valuation
                    </Button>
                    <Button 
                      variant="outline"
                      className="w-full border-border bg-surface hover:bg-elevated/50 text-text-primary h-11 font-bold"
                      onClick={handleExportPDF}
                    >
                      <Download className="mr-2" size={16} />
                      Export PDF Report
                    </Button>
                  </div>
                </CardContent>
              </CardSurface>

              <CardSurface className="">
                <SectionHeader 
                  title="Sensitivity Analysis" 
                  description="Intrinsic Value per Share" 
                  icon={<Info size={16} />} 
                />
                <div className="space-y-4">
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-border hover:bg-transparent">
                          <TableHead className="text-xs uppercase font-bold text-text-muted">WACC \ TGR</TableHead>
                          {Object.keys(Object.values(result.sensitivity_table)[0]).map(tgr => (
                            <TableHead key={tgr} className="text-xs uppercase font-bold text-text-muted text-center">{tgr}</TableHead>
                          ))}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {Object.entries(result.sensitivity_table).map(([wacc, row]) => (
                          <TableRow key={wacc} className="border-border hover:bg-elevated/20 transition-colors">
                            <TableCell className="text-xs font-bold text-text-secondary">{wacc}</TableCell>
                            {Object.values(row).map((val, i) => {
                              const tgrKeys = Object.keys(row);
                              const currentTGRKey = `${(inputs.terminal_growth_rate * 100).toFixed(1)}%`;
                              const currentWACCKey = `${(inputs.wacc * 100).toFixed(1)}%`;
                              const isActiveInput = wacc === currentWACCKey && tgrKeys[i] === currentTGRKey;

                              const marketPrice = result.current_market_price || 0;
                              let cellStyle = 'text-text-muted bg-elevated/20';
                              
                              if (marketPrice > 0) {
                                if (val < 0) {
                                  cellStyle = 'bg-negative/40 text-negative font-bold';
                                } else {
                                  const diff = (val - marketPrice) / marketPrice;
                                  if (diff > 0.5) cellStyle = 'bg-positive text-text-primary font-bold';
                                  else if (diff > 0.05) cellStyle = 'bg-positive/20 text-positive font-semibold';
                                  else if (Math.abs(diff) <= 0.05) cellStyle = 'bg-elevated text-text-primary';
                                  else cellStyle = 'bg-negative/10 text-negative/70';
                                }
                              }

                              return (
                                <TableCell 
                                  key={i} 
                                  className={`text-center text-xs py-2 transition-all border-l border-border font-mono ${cellStyle} ${isActiveInput ? 'ring-2 ring-inset ring-accent z-10' : ''}`}
                                >
                                  {isActiveInput ? (
                                    <strong className="text-text-primary">{currencySymbol}{Math.round(val).toLocaleString('en-US')}</strong>
                                  ) : (
                                    <>{currencySymbol}{Math.round(val).toLocaleString('en-US')}</>
                                  )}
                                </TableCell>
                              );
                            })}
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>

                  {/* Sensitivity Legend */}
                  <div className="flex flex-wrap gap-4 pt-2 border-t border-border">
                    {[
                      { label: 'Undervalued (>50%)', color: 'bg-positive' },
                      { label: 'Undervalued (5-50%)', color: 'bg-positive/20' },
                      { label: 'Fair Value (±5%)', color: 'bg-elevated' },
                      { label: 'Overvalued', color: 'bg-negative/10' },
                    ].map(item => (
                      <div key={item.label} className="flex items-center gap-2">
                        <div className={`w-3 h-3 rounded-sm ${item.color}`} />
                        <span className="text-xs uppercase font-bold text-text-muted tracking-wider">{item.label}</span>
                      </div>
                    ))}
                    <div className="flex items-center gap-2 ml-auto">
                      <div className="w-3 h-3 rounded-sm ring-1 ring-accent" />
                      <span className="text-xs uppercase font-bold text-accent tracking-wider">Current Input</span>
                    </div>
                  </div>
                </div>
              </CardSurface>
            </>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center p-12 border-2 border-dashed border-border rounded-3xl opacity-50 bg-elevated/20">
              <div className="w-16 h-16 bg-elevated rounded-full flex items-center justify-center mb-4">
                <Calculator size={32} className="text-text-muted" />
              </div>
              <h3 className="text-lg font-medium text-text-muted">No calculation yet</h3>
              <p className="text-sm text-text-secondary max-w-[240px] mt-2 font-medium">Enter data in the left panel and click calculate to see results.</p>
            </div>
          )}
        </div>
      </div>
    )}
      {/* HISTORY SECTION */}
      <div className="mt-8">
        <button 
          onClick={() => setIsHistoryOpen(!isHistoryOpen)}
          className="flex items-center gap-2 text-text-muted hover:text-text-primary transition-colors uppercase text-xs font-bold tracking-widest mb-4"
        >
          <History size={16} />
          Recent Valuations
          {isHistoryOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {isHistoryOpen && (
          <CardSurface className="overflow-hidden animate-in fade-in slide-in-from-top-4 duration-300 p-0">
            <Table>
              <TableHeader className="bg-elevated/50">
                <TableRow className="border-border hover:bg-transparent">
                  <TableHead className="text-xs font-bold text-text-muted uppercase">Ticker</TableHead>
                  <TableHead className="text-xs font-bold text-text-muted uppercase">Date</TableHead>
                  <TableHead className="text-xs font-bold text-text-muted uppercase">Intrinsic Value</TableHead>
                  <TableHead className="text-xs font-bold text-text-muted uppercase">Status</TableHead>
                  <TableHead className="text-xs font-bold text-text-muted uppercase text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {history.length > 0 ? (
                  history.map((val) => (
                    <TableRow key={val.id} className="border-border group hover:bg-elevated/20">
                      <TableCell className="font-bold text-text-primary">{val.ticker}</TableCell>
                      <TableCell className="text-text-muted text-xs font-medium">
                        {new Date(val.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="font-mono text-sm font-bold text-text-primary">
                        {formatPrice(val.output_data.intrinsic_value_per_share)}
                      </TableCell>
                      <TableCell>
                        <Badge 
                          variant={val.is_public ? 'success' : 'outline'} 
                          className="cursor-pointer gap-1"
                          onClick={() => handleShare(val.id, val.is_public)}
                        >
                          {val.is_public ? <Globe size={10} /> : null}
                          {val.is_public ? 'Public' : 'Private'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          {val.is_public && (
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="h-8 w-8 text-accent hover:bg-accent/10"
                              onClick={() => copyShareLink(val.id)}
                            >
                              {copiedId === val.id ? <Check size={14} /> : <Share2 size={14} />}
                            </Button>
                          )}
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            className="h-8 w-8 text-text-muted hover:text-negative hover:bg-negative/10"
                            onClick={() => handleDelete(val.id)}
                          >
                            <Trash2 size={14} />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8 text-text-muted italic font-medium">No history found</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardSurface>
        )}
      </div>
    </div>
  );
}
