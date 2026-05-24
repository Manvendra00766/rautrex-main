"use client";

import React, { useEffect, useState } from 'react';
import { useScreenerStore } from '@/store/screenerStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Loader2, Plus, X, Save, TrendingUp, Search } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import Link from 'next/link';
import { ScreenerMetric, ScreenerOperator } from '@/types/screener';

const METRIC_LABELS: Record<ScreenerMetric, string> = {
  pe_ratio: "P/E",
  pb_ratio: "P/B",
  rsi_14: "RSI(14)",
  eps_growth_yoy: "EPS Growth%",
  revenue_growth_yoy: "Revenue Growth%",
  market_cap_cr: "Mkt Cap(₹Cr)",
  week_52_from_high_pct: "% from 52W High"
};

const OPERATOR_LABELS: Record<ScreenerOperator, string> = {
  lt: "<",
  gt: ">",
  lte: "<=",
  gte: ">="
};

export default function StockScreener() {
  const { 
    filters, results, presets, universe, isScreening, isSavingPreset,
    addFilter, removeFilter, updateFilter, setUniverse, runScreener, 
    fetchPresets, savePreset, deletePreset, loadPreset 
  } = useScreenerStore();

  const [presetName, setPresetName] = useState("");
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>(null);

  useEffect(() => {
    fetchPresets();
  }, [fetchPresets]);

  const handleSort = (key: string) => {
    let direction: 'asc' | 'desc' = 'desc';
    if (sortConfig?.key === key && sortConfig.direction === 'desc') {
      direction = 'asc';
    }
    setSortConfig({ key, direction });
  };

  const sortedResults = [...results].sort((a, b) => {
    if (!sortConfig) return 0;
    const { key, direction } = sortConfig;
    const aValue = (a as any)[key] ?? 0;
    const bValue = (b as any)[key] ?? 0;
    return direction === 'asc' ? aValue - bValue : bValue - aValue;
  });

  const getRSIColor = (rsi: number | null) => {
    if (rsi === null) return "";
    if (rsi < 30) return "text-green-500 font-bold";
    if (rsi > 70) return "text-red-500 font-bold";
    return "";
  };

  const get52WColor = (pct: number | null) => {
    if (pct === null) return "";
    if (pct > -5) return "text-green-500 font-bold";
    if (pct < -20) return "text-red-500 font-bold";
    return "";
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 p-4">
      {/* Left Panel - Filters */}
      <Card className="lg:col-span-4 h-fit">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="w-5 h-5" />
            Screener Filters
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Universe Selection */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Market Universe</label>
            <div className="flex gap-2">
              <Button 
                variant={universe === "nifty50" ? "default" : "outline"}
                size="sm"
                className="flex-1"
                onClick={() => setUniverse("nifty50")}
              >
                Nifty 50
              </Button>
              <Button 
                variant={universe === "nifty100" ? "default" : "outline"}
                size="sm"
                className="flex-1"
                onClick={() => setUniverse("nifty100")}
              >
                Nifty 100
              </Button>
            </div>
          </div>

          {/* Filter Rows */}
          <div className="space-y-3">
            {filters.map((filter, index) => (
              <div key={index} className="flex gap-2 items-center">
                <select 
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  value={filter.metric}
                  onChange={(e) => updateFilter(index, { metric: e.target.value as ScreenerMetric })}
                >
                  {Object.entries(METRIC_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>

                <select 
                  className="flex h-9 w-20 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  value={filter.operator}
                  onChange={(e) => updateFilter(index, { operator: e.target.value as ScreenerOperator })}
                >
                  {Object.entries(OPERATOR_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>

                <Input 
                  type="number" 
                  className="w-24"
                  value={filter.value}
                  onChange={(e) => updateFilter(index, { value: parseFloat(e.target.value) || 0 })}
                />

                <Button variant="ghost" size="icon" onClick={() => removeFilter(index)}>
                  <X className="w-4 h-4 text-muted-foreground" />
                </Button>
              </div>
            ))}

            <Button 
              variant="outline" 
              className="w-full border-dashed" 
              onClick={addFilter}
              disabled={filters.length >= 5}
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Filter {filters.length >= 5 && "(Max 5)"}
            </Button>
          </div>

          <Button 
            className="w-full" 
            onClick={runScreener}
            disabled={isScreening}
          >
            {isScreening ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <TrendingUp className="w-4 h-4 mr-2" />}
            Run Screener
          </Button>

          {/* Presets */}
          <div className="pt-4 border-t space-y-4">
            <div className="flex gap-2">
              <Input 
                placeholder="Preset name..." 
                value={presetName}
                onChange={(e) => setPresetName(e.target.value)}
              />
              <Button 
                variant="secondary" 
                size="icon"
                onClick={() => {
                  if (presetName) {
                    savePreset(presetName);
                    setPresetName("");
                  }
                }}
                disabled={isSavingPreset || !presetName || filters.length === 0}
              >
                {isSavingPreset ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              </Button>
            </div>

            <div className="flex flex-wrap gap-2">
              {presets.map((p) => (
                <div key={p.id} className="group relative">
                  <Badge 
                    variant="secondary" 
                    className="cursor-pointer pr-6 hover:bg-secondary/80"
                    onClick={() => loadPreset(p)}
                  >
                    {p.name}
                  </Badge>
                  <button 
                    className="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => {
                      e.stopPropagation();
                      deletePreset(p.id);
                    }}
                  >
                    <X className="w-3 h-3 text-red-500" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Right Panel - Results */}
      <Card className="lg:col-span-8">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Screener Results</CardTitle>
          <Badge variant="outline">{results.length} stocks match</Badge>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="cursor-pointer" onClick={() => handleSort('company_name')}>Company</TableHead>
                  <TableHead className="cursor-pointer text-right" onClick={() => handleSort('current_price')}>Price</TableHead>
                  <TableHead className="cursor-pointer text-right" onClick={() => handleSort('pe_ratio')}>P/E</TableHead>
                  <TableHead className="cursor-pointer text-right" onClick={() => handleSort('pb_ratio')}>P/B</TableHead>
                  <TableHead className="cursor-pointer text-right" onClick={() => handleSort('rsi_14')}>RSI</TableHead>
                  <TableHead className="cursor-pointer text-right" onClick={() => handleSort('market_cap_cr')}>Mkt Cap</TableHead>
                  <TableHead className="cursor-pointer text-right" onClick={() => handleSort('week_52_from_high_pct')}>52W%</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedResults.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="h-24 text-center text-muted-foreground">
                      No results found. Adjust filters and run screener.
                    </TableCell>
                  </TableRow>
                ) : (
                  sortedResults.map((stock) => (
                    <TableRow key={stock.ticker}>
                      <TableCell className="font-medium">
                        <div className="flex flex-col">
                          <span>{stock.company_name}</span>
                          <span className="text-xs text-muted-foreground">{stock.ticker}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        ₹{stock.current_price?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </TableCell>
                      <TableCell className="text-right">{stock.pe_ratio?.toFixed(1) || '-'}</TableCell>
                      <TableCell className="text-right">{stock.pb_ratio?.toFixed(2) || '-'}</TableCell>
                      <TableCell className={`text-right ${getRSIColor(stock.rsi_14)}`}>
                        {stock.rsi_14?.toFixed(1) || '-'}
                      </TableCell>
                      <TableCell className="text-right">
                        ₹{Math.round(stock.market_cap_cr || 0).toLocaleString('en-IN')}Cr
                      </TableCell>
                      <TableCell className={`text-right ${get52WColor(stock.week_52_from_high_pct)}`}>
                        {stock.week_52_from_high_pct?.toFixed(1)}%
                      </TableCell>
                      <TableCell className="text-right">
                        <Link href={`/dashboard/dcf?ticker=${stock.ticker}`}>
                          <Button size="sm" variant="ghost">Run DCF</Button>
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
