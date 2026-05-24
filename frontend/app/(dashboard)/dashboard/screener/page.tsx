'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { useScreenerStore } from '@/store/screenerStore';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Loader2, Filter, Search, RefreshCcw, ArrowUpDown, Download, ExternalLink } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function ScreenerPage() {
  const router = useRouter();
  const { filters, results, loading, error, setFilter, runScreener, resetFilters, cacheStatus, clearCache } = useScreenerStore();
  const [sortConfig, setSortConfig] = useState<{key: string, direction: 'asc' | 'desc'}>({
    key: 'dcf_margin_of_safety',
    direction: 'desc'
  });
  const [hasRun, setHasRun] = useState(false);

  // Manual Trigger only
  const handleRunScreener = async () => {
    setHasRun(true);
    await runScreener();
  };

  const handleReset = () => {
    resetFilters();
    setHasRun(false);
  };

  const handleFilterChange = (key: any, value: string) => {
    const numValue = value === '' ? undefined : parseFloat(value);
    setFilter(key, numValue);
  };

  const formatCurrency = (val: number | null) => {
    if (val === null) return '-';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const formatCr = (val: number | null) => {
    if (val === null) return '-';
    return new Intl.NumberFormat('en-IN', {
      maximumFractionDigits: 0,
    }).format(val) + ' Cr';
  };

  const getSignalBadge = (stock: any) => {
    const margin = stock.dcf_margin_of_safety;
    if (margin === null || margin === undefined) return <Badge variant="secondary">N/A</Badge>;
    
    if (margin > 30) return <Badge className="bg-emerald-600 hover:bg-emerald-700 text-white border-0">STRONG BUY</Badge>;
    if (margin > 10) return <Badge className="bg-teal-500 hover:bg-teal-600 text-white border-0">BUY</Badge>;
    if (margin > -10) return <Badge variant="outline" className="text-muted-foreground border-muted-foreground/30">FAIR</Badge>;
    return <Badge variant="destructive" className="bg-red-500/80 hover:bg-red-600 border-0">OVERVALUED</Badge>;
  };

  const handleSort = (key: string) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc'
    }));
  };

  const sortedResults = useMemo(() => {
    const sortable = [...results];
    sortable.sort((a: any, b: any) => {
      const aVal = a[sortConfig.key];
      const bVal = b[sortConfig.key];
      
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;
      
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
    return sortable;
  }, [results, sortConfig]);

  const handleExportCSV = () => {
    if (results.length === 0) return;
    const headers = ['Symbol', 'Company', 'Price', 'P/E', 'ROE%', 'RSI', 'Market Cap (Cr)', 'DCF Margin%', 'Signal'];
    const rows = results.map(r => [
      r.symbol,
      r.company_name.replace(/,/g, ''),
      r.current_price,
      r.pe_ratio,
      r.roe,
      r.rsi,
      r.market_cap,
      r.dcf_margin_of_safety,
      r.signal
    ]);
    
    const csvContent = [headers, ...rows].map(e => e.join(",")).join("\n");
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `screener_results_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const avgPE = useMemo(() => {
    const valid = results.filter(r => r.pe_ratio !== null);
    return valid.length ? (valid.reduce((sum, r) => sum + (r.pe_ratio || 0), 0) / valid.length).toFixed(1) : '-';
  }, [results]);

  const avgRSI = useMemo(() => {
    const valid = results.filter(r => r.rsi !== null);
    return valid.length ? (valid.reduce((sum, r) => sum + (r.rsi || 0), 0) / valid.length).toFixed(1) : '-';
  }, [results]);

  const undervaluedCount = useMemo(() => {
    return results.filter(r => (r.dcf_margin_of_safety || 0) > 0).length;
  }, [results]);

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Institutional Stock Screener</h1>
        <p className="text-muted-foreground">
          Advanced multi-factor filtering across Nifty 50 universe with DCF intrinsic value analysis.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Filter Panel */}
        <Card className="md:col-span-1 h-fit">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Filter className="w-4 h-4" /> Filters
            </CardTitle>
            <CardDescription>Adjust metrics to find opportunities</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="space-y-2">
              <Label>P/E Ratio (Range)</Label>
              <div className="flex gap-2">
                <Input 
                  placeholder="Min" 
                  type="number" 
                  value={filters.min_pe || ''} 
                  onChange={(e) => handleFilterChange('min_pe', e.target.value)}
                />
                <Input 
                  placeholder="Max" 
                  type="number" 
                  value={filters.max_pe || ''} 
                  onChange={(e) => handleFilterChange('max_pe', e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>ROE % (Min)</Label>
              <Input 
                placeholder="e.g. 15" 
                type="number" 
                value={filters.min_roe || ''} 
                onChange={(e) => handleFilterChange('min_roe', e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>RSI 14 (Range)</Label>
              <div className="flex gap-2">
                <Input 
                  placeholder="Min" 
                  type="number" 
                  value={filters.min_rsi || ''} 
                  onChange={(e) => handleFilterChange('min_rsi', e.target.value)}
                />
                <Input 
                  placeholder="Max" 
                  type="number" 
                  value={filters.max_rsi || ''} 
                  onChange={(e) => handleFilterChange('max_rsi', e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>DCF Margin % (Min)</Label>
              <Input 
                placeholder="e.g. 20" 
                type="number" 
                value={filters.min_dcf_margin_of_safety || ''} 
                onChange={(e) => handleFilterChange('min_dcf_margin_of_safety', e.target.value)}
              />
            </div>

            <div className="pt-4 flex flex-col gap-2">
              <button 
                onClick={handleRunScreener}
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '12px',
                  background: 'var(--accent-teal)',
                  color: 'var(--bg-surface)',
                  fontWeight: 600,
                  fontSize: '14px',
                  borderRadius: '8px',
                  border: 'none',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  marginBottom: '8px',
                  opacity: loading ? 0.7 : 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px'
                }}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Scanning...
                  </>
                ) : (
                  <>
                    <Search className="w-4 h-4" />
                    Run Screener
                  </>
                )}
              </button>
              <Button onClick={handleReset} variant="outline" className="w-full">
                <RefreshCcw className="w-4 h-4 mr-2" /> Reset
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Results Table */}
        <Card className="md:col-span-3">
          <CardHeader>
            <div className="flex justify-between items-center">
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-3">
                  <CardTitle>Screening Results</CardTitle>
                  {cacheStatus && (
                    <Badge variant="outline" className="text-[10px] font-mono opacity-70">
                      {cacheStatus}
                    </Badge>
                  )}
                </div>
                <CardDescription>
                  {hasRun ? `Found ${results.length} stocks matching your criteria` : "Results will appear here"}
                </CardDescription>
              </div>
              <div className="flex items-center gap-3">
                {error && <span className="text-destructive text-sm font-medium">{error}</span>}
                {hasRun && (
                  <>
                    <Button variant="outline" size="sm" onClick={handleExportCSV} className="h-8 text-xs">
                      <Download className="w-3.5 h-3.5 mr-1.5" /> Export CSV
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="h-8 text-xs text-muted-foreground hover:text-primary"
                      onClick={clearCache}
                      disabled={loading}
                    >
                      <RefreshCcw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
                      Refresh Data
                    </Button>
                  </>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <div className="relative mb-6">
                  <div className="w-16 h-16 border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
                  <Search className="w-6 h-6 text-primary absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
                </div>
                <h3 className="text-xl font-bold mb-2">Scanning NIFTY 50...</h3>
                <p className="text-muted-foreground max-w-xs mx-auto">
                  Crunching data and DCF models for 50 stocks. This may take 15-30 seconds.
                </p>
              </div>
            ) : !hasRun ? (
              <div className="flex flex-col items-center justify-center py-24 text-center border-2 border-dashed rounded-lg bg-muted/5">
                <Filter className="w-12 h-12 text-muted-foreground mb-4 opacity-20" />
                <h3 className="text-lg font-semibold">Ready to Scan</h3>
                <p className="text-muted-foreground max-w-sm">
                  Set your multi-factor filters and click <span className="text-primary font-bold">Run Screener</span> to find institutional-grade opportunities.
                </p>
              </div>
            ) : sortedResults.length > 0 ? (
              <div className="space-y-4">
                <div className="rounded-md border overflow-hidden">
                  <Table>
                    <TableHeader className="bg-muted/50">
                      <TableRow>
                        <TableHead className="w-12 text-center">#</TableHead>
                        <TableHead className="cursor-pointer hover:text-primary transition-colors" onClick={() => handleSort('symbol')}>
                          Symbol {sortConfig.key === 'symbol' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                        </TableHead>
                        <TableHead>Company</TableHead>
                        <TableHead className="text-right cursor-pointer hover:text-primary transition-colors" onClick={() => handleSort('current_price')}>
                          Price {sortConfig.key === 'current_price' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                        </TableHead>
                        <TableHead className="text-right cursor-pointer hover:text-primary transition-colors" onClick={() => handleSort('pe_ratio')}>
                          P/E {sortConfig.key === 'pe_ratio' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                        </TableHead>
                        <TableHead className="text-right cursor-pointer hover:text-primary transition-colors" onClick={() => handleSort('roe')}>
                          ROE% {sortConfig.key === 'roe' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                        </TableHead>
                        <TableHead className="text-right cursor-pointer hover:text-primary transition-colors" onClick={() => handleSort('rsi')}>
                          RSI {sortConfig.key === 'rsi' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                        </TableHead>
                        <TableHead className="text-right cursor-pointer hover:text-primary transition-colors" onClick={() => handleSort('market_cap')}>
                          Cap (Cr) {sortConfig.key === 'market_cap' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                        </TableHead>
                        <TableHead className="text-right">
                          Intrinsic
                        </TableHead>
                        <TableHead className="text-right cursor-pointer hover:text-primary transition-colors font-bold" onClick={() => handleSort('dcf_margin_of_safety')}>
                          Margin% {sortConfig.key === 'dcf_margin_of_safety' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                        </TableHead>
                        <TableHead className="text-center">Signal</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {sortedResults.map((stock, idx) => (
                        <TableRow 
                          key={stock.symbol} 
                          className="cursor-pointer hover:bg-muted/30 transition-colors group"
                          onClick={() => router.push(`/dashboard/dcf?ticker=${stock.symbol.replace('.NS', '')}`)}
                        >
                          <TableCell className="text-center text-muted-foreground text-xs">{idx + 1}</TableCell>
                          <TableCell className="font-bold">
                            <div className="flex items-center gap-1">
                              {stock.symbol.replace('.NS', '')}
                              <ExternalLink className="w-2.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity text-primary" />
                            </div>
                          </TableCell>
                          <TableCell className="max-w-[150px] truncate text-xs">{stock.company_name}</TableCell>
                          <TableCell className="text-right font-mono">{formatCurrency(stock.current_price)}</TableCell>
                          <TableCell className="text-right">{stock.pe_ratio?.toFixed(1) || '-'}</TableCell>
                          <TableCell className="text-right">{(stock.roe || 0).toFixed(1)}%</TableCell>
                          <TableCell className="text-right">{stock.rsi?.toFixed(1) || '-'}</TableCell>
                          <TableCell className="text-right text-xs">{formatCr(stock.market_cap)}</TableCell>
                          <TableCell className="text-right font-mono text-xs">
                            {stock.current_price && stock.dcf_margin_of_safety ? 
                              formatCurrency(stock.current_price * (1 + stock.dcf_margin_of_safety / 100)) : 
                              '-'}
                          </TableCell>
                          <TableCell className="text-right font-bold">
                            <span className={stock.dcf_margin_of_safety && stock.dcf_margin_of_safety > 0 ? 'text-emerald-500' : 'text-red-500'}>
                              {stock.dcf_margin_of_safety?.toFixed(1) || '-'}%
                            </span>
                          </TableCell>
                          <TableCell className="text-center">{getSignalBadge(stock)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
                <div className="flex items-center justify-between px-2 text-[11px] text-muted-foreground font-medium uppercase tracking-wider">
                   <div className="flex gap-4">
                     <span>Showing {results.length} stocks</span>
                     <span>Avg P/E: {avgPE}</span>
                     <span>Avg RSI: {avgRSI}</span>
                   </div>
                   <div className="text-emerald-500 font-bold">
                     {undervaluedCount} Undervalued Opportunities Found
                   </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-20 text-center border-2 border-dashed rounded-lg">
                <Search className="w-12 h-12 text-muted-foreground mb-4 opacity-20" />
                <h3 className="text-lg font-semibold">No stocks match your filters</h3>
                <p className="text-muted-foreground">Try widening the criteria to find opportunities.</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
