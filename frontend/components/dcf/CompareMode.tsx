"use client"

import React, { useState } from 'react'
import { useDCFStore } from '@/store/dcfStore'
import { DCFInput, DCFOutput } from '@/types/dcf'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/components/ui/Toast'
import { formatError } from '@/lib/utils'
import { 
  LineChart, Line, ResponsiveContainer, Tooltip as RechartsTooltip 
} from 'recharts'
import ChartWrapper from '@/components/ChartWrapper';
import { 
  Loader2, Calculator, ArrowRightLeft, TrendingUp, TrendingDown, Check, AlertTriangle 
} from 'lucide-react'

const initialStock: DCFInput = {
  ticker: '',
  revenue: [0, 0, 0],
  ebit_margin: 0.18,
  tax_rate: 0.25,
  capex_pct: 0.08,
  nwc_change_pct: 0.02,
  wacc: 0.12,
  terminal_growth_rate: 0.04,
  projection_years: 5,
  shares_outstanding: 100,
  net_debt: 0,
};

export default function CompareMode() {
  const [stockA, setStockA] = useState<DCFInput>({ ...initialStock })
  const [stockB, setStockB] = useState<DCFInput>({ ...initialStock })
  const { compare, compareResult, isComparing } = useDCFStore()
  const { toast } = useToast()
  const [isFetchingA, setIsFetchingA] = useState(false)
  const [isFetchingB, setIsFetchingB] = useState(false)
  const [isMounted, setIsMounted] = useState(false)

  React.useEffect(() => {
    setIsMounted(true)
  }, [])

  const fetchFinancials = async (ticker: string, setStock: (s: DCFInput) => void, setIsFetching: (b: boolean) => void) => {
    if (!ticker || ticker.length < 2) return;
    setIsFetching(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/stocks/${ticker.toUpperCase()}`);
      if (!response.ok) throw new Error('Ticker not found');
      const data = await response.json();
      
      setStock(prev => ({
        ...prev,
        ticker: data.ticker,
        revenue: data.revenue.length > 0 ? data.revenue : prev.revenue,
        ebit_margin: data.ebit_margin || prev.ebit_margin,
        tax_rate: data.tax_rate || prev.tax_rate,
        capex_pct: data.capex_pct || prev.capex_pct,
        da_pct: data.da_pct || prev.da_pct,
        nwc_change_pct: data.nwc_change_pct || prev.nwc_change_pct,
        shares_outstanding: data.shares_outstanding || prev.shares_outstanding,
        net_debt: data.net_debt || prev.net_debt,
      }));

      toast({ type: 'success', title: 'Data Loaded', description: `Financials for ${data.ticker} populated.` });
    } catch (error) {
      toast({ type: 'info', title: 'Manual Entry', description: `Could not fetch data for ${ticker}` });
    } finally {
      setIsFetching(false);
    }
  };

  const handleApplyAtoB = () => {
    setStockB({ 
      ...stockB, 
      ebit_margin: stockA.ebit_margin,
      tax_rate: stockA.tax_rate,
      capex_pct: stockA.capex_pct,
      da_pct: stockA.da_pct || 0.03,
      nwc_change_pct: stockA.nwc_change_pct,
      wacc: stockA.wacc,
      terminal_growth_rate: stockA.terminal_growth_rate,
      projection_years: stockA.projection_years
    })
    toast({ type: 'info', title: 'Assumptions Synced', description: 'Stock B now uses assumptions from Stock A.' })
  }

  const handleCompare = async () => {
    if (!stockA.ticker || !stockB.ticker) {
      toast({ type: 'error', title: 'Tickers Required', description: 'Enter tickers for both stocks.' })
      return
    }

    // Ensure we have revenue data
    if (stockA.revenue.every(r => r === 0) || stockB.revenue.every(r => r === 0)) {
        toast({ type: 'info', title: 'Fetching Data', description: 'Retrieving financials before calculation...' });
        await Promise.all([
            fetchFinancials(stockA.ticker, setStockA, setIsFetchingA),
            fetchFinancials(stockB.ticker, setStockB, setIsFetchingB)
        ]);
    }

    try {
      await compare(stockA, stockB)
      toast({ type: 'success', title: 'Comparison Ready' })
    } catch (error: any) {
      toast({ type: 'error', title: 'Comparison Failed', description: formatError(error) })
    }
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Input A */}
        <Card className="glass-panel border-white/5 bg-[#0d0d14]">
          <CardHeader className="pb-4">
            <CardTitle className="text-sm uppercase tracking-widest text-primary">Stock A</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Ticker</Label>
              <div className="relative">
                <Input 
                  value={stockA.ticker} 
                  onChange={e => setStockA({ ...stockA, ticker: e.target.value.toUpperCase() })}
                  onBlur={() => fetchFinancials(stockA.ticker, setStockA, setIsFetchingA)}
                  className="bg-surface/50 border-white/10 pr-10"
                />
                {isFetchingA && <Loader2 size={16} className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-primary" />}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label className="text-xs">WACC (%)</Label>
                <Input type="number" value={stockA.wacc * 100} onChange={e => setStockA({ ...stockA, wacc: parseFloat(e.target.value) / 100 })} className="h-8 bg-surface/50 border-white/10" />
              </div>
              <div className="space-y-2">
                <Label className="text-xs">TGR (%)</Label>
                <Input type="number" value={stockA.terminal_growth_rate * 100} onChange={e => setStockA({ ...stockA, terminal_growth_rate: parseFloat(e.target.value) / 100 })} className="h-8 bg-surface/50 border-white/10" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Input B */}
        <Card className="glass-panel border-white/5 bg-[#0d0d14]">
          <CardHeader className="pb-4 flex flex-row items-center justify-between">
            <CardTitle className="text-sm uppercase tracking-widest text-accent">Stock B</CardTitle>
            <Button variant="ghost" size="sm" className="h-7 text-xs text-gray-500 hover:text-white" onClick={handleApplyAtoB}>
              <ArrowRightLeft size={12} className="mr-1" /> Use A's Assumptions
            </Button>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Ticker</Label>
              <div className="relative">
                <Input 
                  value={stockB.ticker} 
                  onChange={e => setStockB({ ...stockB, ticker: e.target.value.toUpperCase() })}
                  onBlur={() => fetchFinancials(stockB.ticker, setStockB, setIsFetchingB)}
                  className="bg-surface/50 border-white/10 pr-10"
                />
                {isFetchingB && <Loader2 size={16} className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-accent" />}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label className="text-xs">WACC (%)</Label>
                <Input type="number" value={stockB.wacc * 100} onChange={e => setStockB({ ...stockB, wacc: parseFloat(e.target.value) / 100 })} className="h-8 bg-surface/50 border-white/10" />
              </div>
              <div className="space-y-2">
                <Label className="text-xs">TGR (%)</Label>
                <Input type="number" value={stockB.terminal_growth_rate * 100} onChange={e => setStockB({ ...stockB, terminal_growth_rate: parseFloat(e.target.value) / 100 })} className="h-8 bg-surface/50 border-white/10" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="relative group">
        <div className={`absolute -inset-1 bg-primary/20 rounded-xl blur-lg transition-all duration-1000 ${compareResult === null ? 'animate-pulse opacity-100' : 'opacity-0'}`} />
        <Button 
          className="relative w-full bg-[#00BCD4] hover:bg-[#00ACC1] text-[#0a0a0a] font-semibold text-[15px] h-14 rounded-lg shadow-xl" 
          onClick={handleCompare}
          disabled={isComparing}
        >
          {isComparing ? <Loader2 className="animate-spin mr-2" /> : <Calculator className="mr-2" size={20} />}
          RUN COMPARISON
        </Button>
      </div>

      {compareResult && (
        <div className="space-y-6 animate-in slide-in-from-bottom-4 duration-700">
          {/* Winner Banner */}
          <div className={`p-4 rounded-2xl border flex items-center justify-center gap-3 font-bold ${
            compareResult.winner === 'equal' 
              ? 'bg-yellow-500/10 border-yellow-500/20 text-yellow-500' 
              : 'bg-green-500/10 border-green-500/20 text-green-500'
          }`}>
            {compareResult.winner === 'equal' ? (
              <><AlertTriangle size={20} /> Both stocks trade near fair value</>
            ) : (
              <><Check size={20} /> {compareResult.winner} is the better buy by {compareResult.upside_difference_pct}%</>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <ResultCard output={compareResult.output_a} />
            <ResultCard output={compareResult.output_b} />
          </div>

          {/* Relative Upside Bar */}
          <div className="glass-panel p-6 rounded-2xl bg-[#0d0d14]">
            <h4 className="text-xs uppercase font-bold text-gray-500 mb-4 tracking-widest text-center">Relative Upside Comparison</h4>
            <div className="flex h-4 w-full rounded-full overflow-hidden bg-white/5">
              <UpsideBarPart ticker={compareResult.output_a.ticker} upside={compareResult.output_a.upside_downside_pct || 0} />
              <UpsideBarPart ticker={compareResult.output_b.ticker} upside={compareResult.output_b.upside_downside_pct || 0} />
            </div>
            <div className="flex justify-between mt-2 text-xs font-bold">
              <span className="text-primary">{compareResult.output_a.ticker} ({(compareResult.output_a.upside_downside_pct! * 100).toFixed(1)}%)</span>
              <span className="text-accent">{compareResult.output_b.ticker} ({(compareResult.output_b.upside_downside_pct! * 100).toFixed(1)}%)</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ResultCard({ output }: { output: DCFOutput }) {
  const currencySymbol = output.currency === 'INR' ? '₹' : '$';
  const locale = output.currency === 'INR' ? 'en-IN' : 'en-US';
  const unit = output.unit;

  const hasNegativeFCF = output.projected_fcfs.some(f => f < 0);

  return (
    <Card className="glass-panel border-white/5 bg-[#11111a] relative overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-xl font-black">{output.ticker}</CardTitle>
        <Badge variant={(output.upside_downside_pct || 0) > 0 ? 'success' : 'error'}>
          {((output.upside_downside_pct || 0) * 100).toFixed(1)}%
        </Badge>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col mb-4">
          <span className={`text-3xl font-black ${output.intrinsic_value_per_share < 0 ? 'text-red-500' : 'text-white'}`}>
            {output.intrinsic_value_per_share.toLocaleString(locale, { style: 'currency', currency: output.currency })}
          </span>
          <span className="text-xs text-gray-500">Market: {output.current_market_price?.toLocaleString(locale, { style: 'currency', currency: output.currency }) || 'N/A'}</span>
        </div>

        {hasNegativeFCF && (
          <div className="mb-4 p-2 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-2 text-xs text-red-500 font-bold uppercase tracking-tight">
            <AlertTriangle size={12} />
            ⚠ Negative FCF Warning
          </div>
        )}
        
        {output.warnings && output.warnings.length > 0 && (
           <div className="mb-4 p-2 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
             <div className="flex items-center gap-1 text-yellow-500 text-xs font-bold uppercase mb-1">
               <AlertTriangle size={10} /> Data Quality: {output.data_quality_score}
             </div>
             <ul className="list-disc pl-4 text-xs text-yellow-500/80 space-y-0.5">
               {output.warnings.slice(0, 2).map((w, i) => <li key={i} className="truncate">{w}</li>)}
               {output.warnings.length > 2 && <li>+ {output.warnings.length - 2} more...</li>}
             </ul>
           </div>
        )}

        <div className="h-20 w-full mb-4" style={{ minHeight: '80px' }}>
          {isMounted ? (
            <ChartWrapper height={300}>
<ResponsiveContainer width="100%" height="100%">
              <LineChart data={output.projected_fcfs.map((f, i) => ({ y: i, f }))}>
                <RechartsTooltip 
                  contentStyle={{ backgroundColor: '#0d0d14', border: 'none', borderRadius: '8px' }}
                  itemStyle={{ fontSize: '10px' }}
                  labelStyle={{ display: 'none' }}
                  formatter={(val: number) => [val.toLocaleString(locale) + ` ${unit}`, 'FCF']}
                />
                <Line type="monotone" dataKey="f" stroke={hasNegativeFCF ? '#ef4444' : '#00d4ff'} strokeWidth={2} dot={{ r: 3, fill: hasNegativeFCF ? '#ef4444' : '#00d4ff' }} />
              </LineChart>
            </ResponsiveContainer>
</ChartWrapper>
          ) : (
            <div className="w-full h-full bg-white/5 rounded-lg animate-pulse" />
          )}
        </div>

        <div className="grid grid-cols-2 gap-4 text-xs">
          <div>
            <span className="text-gray-500 uppercase font-bold block">Enterprise Value</span>
            <span className="text-white font-black">{output.enterprise_value.toLocaleString(locale)} {unit}</span>
          </div>
          <div>
            <span className="text-gray-500 uppercase font-bold block">Terminal Value</span>
            <span className="text-white font-black">{output.terminal_value.toLocaleString(locale)} {unit}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function UpsideBarPart({ ticker, upside }: { ticker: string, upside: number }) {
  const width = Math.max(5, Math.min(95, (upside + 1) * 50)) // Rough normalization
  return (
    <div 
      className={`h-full transition-all duration-1000 ${upside > 0 ? 'bg-primary' : 'bg-red-500 opacity-50'}`}
      style={{ width: `${width}%` }}
    />
  )
}
