import { notFound } from 'next/navigation';
import { Metadata } from 'next';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { TrendingUp, TrendingDown, Info, Calculator, Globe } from 'lucide-react';
import ShareableFCFChart from '@/components/dcf/ShareableFCFChart';
import { SavedValuation } from '@/types/dcf';

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  const valuation = await getPublicValuation(params.id);
  if (!valuation) return { title: 'Valuation Not Found' };
  
  return {
    title: `${valuation.ticker} DCF Valuation | Rautrex`,
    description: `Intrinsic value estimate for ${valuation.ticker} using professional DCF models.`,
  };
}

async function getPublicValuation(id: string): Promise<SavedValuation | null> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  try {
    const res = await fetch(`${baseUrl}/dcf/public/${id}`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch (error) {
    return null;
  }
}

export default async function SharedValuationPage({ params }: { params: { id: string } }) {
  const valuation = await getPublicValuation(params.id);

  if (!valuation) {
    notFound();
  }

  const { output_data: result, input_data: inputs } = valuation;

  const formatPrice = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2
    }).format(val);
  };

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(val) + ' Cr';
  };

  return (
    <div className="min-h-screen bg-background text-white p-6 md:p-12">
      <div className="max-w-6xl mx-auto space-y-12">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-white/5 pb-8">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <Calculator className="text-primary" size={28} />
              <h1 className="text-4xl font-black tracking-tighter uppercase">Rautrex Valuation</h1>
            </div>
            <p className="text-gray-500 font-medium flex items-center gap-2">
              <Globe size={14} /> Public Shared Analysis • Generated on {new Date(valuation.created_at).toLocaleDateString('en-IN')}
            </p>
          </div>
          
          <div className="flex flex-col items-end gap-1">
            <span className="text-sm text-gray-500 uppercase tracking-widest font-bold">Intrinsic Value</span>
            <div className="flex items-center gap-4">
               <span className="text-5xl font-black">{formatPrice(result.intrinsic_value_per_share)}</span>
               {result.upside_downside_pct !== null && (
                <Badge variant={result.upside_downside_pct > 0 ? 'success' : 'error'} className="text-lg py-1 px-3">
                  {result.upside_downside_pct > 0 ? <TrendingUp size={18} className="mr-1" /> : <TrendingDown size={18} className="mr-1" />}
                  {(result.upside_downside_pct * 100).toFixed(1)}%
                </Badge>
              )}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Chart and Sensitivity */}
          <div className="lg:col-span-2 space-y-8">
            <Card className="glass-panel bg-[#0d0d14] border-white/5">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  Projected Free Cash Flows ({valuation.ticker})
                </CardTitle>
                <CardDescription>Estimated annual FCFF for the next {inputs.projection_years} years</CardDescription>
              </CardHeader>
              <CardContent>
                <ShareableFCFChart 
                  projected_fcfs={result.projected_fcfs} 
                  projection_years={inputs.projection_years} 
                />
                
                <div className="grid grid-cols-3 gap-4 mt-8 pt-8 border-t border-white/5">
                  {[
                    { label: 'Enterprise Value', value: result.enterprise_value },
                    { label: 'Equity Value', value: result.equity_value },
                    { label: 'Net Debt', value: inputs.net_debt },
                  ].map(item => (
                    <div key={item.label} className="text-center">
                      <span className="text-[10px] text-gray-500 uppercase block mb-1 font-bold">{item.label}</span>
                      <span className="text-lg font-black text-white">{formatCurrency(item.value)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="glass-panel bg-[#0d0d14] border-white/5">
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <Info size={16} className="text-primary" />
                  Sensitivity Table (WACC vs Terminal Growth)
                </CardTitle>
              </CardHeader>
              <CardContent>
                 <Table>
                    <TableHeader>
                      <TableRow className="border-white/5 hover:bg-transparent">
                        <TableHead className="text-[10px] uppercase font-bold text-gray-500">WACC \ TGR</TableHead>
                        {Object.keys(Object.values(result.sensitivity_table)[0]).map(tgr => (
                          <TableHead key={tgr} className="text-[10px] uppercase font-bold text-gray-500 text-center">{tgr}</TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {Object.entries(result.sensitivity_table).map(([wacc, row]) => (
                        <TableRow key={wacc} className="border-white/5 hover:bg-white/5">
                          <TableCell className="text-xs font-bold text-gray-400">{wacc}</TableCell>
                          {Object.values(row).map((val, i) => {
                             const marketPrice = result.current_market_price || 0;
                             let textColor = 'text-white';
                             if (marketPrice > 0) {
                               if (val > marketPrice * 1.05) textColor = 'text-green-500';
                               else if (val < marketPrice * 0.95) textColor = 'text-red-500';
                             }
                             return (
                               <TableCell key={i} className={`text-center text-xs font-mono font-bold ${textColor}`}>
                                 {val.toLocaleString('en-IN')}
                               </TableCell>
                             );
                          })}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
              </CardContent>
            </Card>
          </div>

          {/* Model Inputs sidebar */}
          <div className="space-y-8">
            <Card className="glass-panel bg-[#0d0d14] border-white/5 h-full">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-widest text-primary">Model Assumptions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {[
                  { label: 'WACC (Discount Rate)', value: `${(inputs.wacc * 100).toFixed(1)}%` },
                  { label: 'Terminal Growth', value: `${(inputs.terminal_growth_rate * 100).toFixed(1)}%` },
                  { label: 'EBIT Margin', value: `${(inputs.ebit_margin * 100).toFixed(1)}%` },
                  { label: 'Tax Rate', value: `${(inputs.tax_rate * 100).toFixed(1)}%` },
                  { label: 'CapEx % of Rev', value: `${(inputs.capex_pct * 100).toFixed(1)}%` },
                  { label: 'Shares Out.', value: `${inputs.shares_outstanding} Cr` },
                ].map(item => (
                  <div key={item.label} className="flex justify-between items-center border-b border-white/5 pb-3">
                    <span className="text-xs text-gray-500 font-medium">{item.label}</span>
                    <span className="text-sm font-black text-white">{item.value}</span>
                  </div>
                ))}

                <div className="pt-6">
                  <div className="bg-primary/10 border border-primary/20 rounded-2xl p-4 text-center">
                    <p className="text-[10px] text-primary uppercase font-bold mb-1">Market Sentiment</p>
                    <p className="text-sm text-white font-medium italic">
                      "Analysis suggests {valuation.ticker} is currently {result.upside_downside_pct! > 0 ? 'undervalued' : 'overvalued'} based on these parameters."
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        <div className="text-center pt-12 text-gray-600">
          <p className="text-xs">© 2026 Rautrex Financial Analytics • For educational purposes only.</p>
        </div>
      </div>
    </div>
  );
}
