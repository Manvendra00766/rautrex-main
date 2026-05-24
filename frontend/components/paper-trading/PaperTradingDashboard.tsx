"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  Cell 
} from 'recharts';
import { 
  Wallet, 
  TrendingUp, 
  Briefcase, 
  History, 
  RefreshCcw, 
  Loader2,
  ChevronDown,
  ChevronUp,
  AlertCircle
} from 'lucide-react';
import { usePaperTradingStore } from '@/store/paperTradingStore';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useToast } from '@/components/ui/Toast';
import { cn } from '@/lib/utils';
import ChartWrapper from '@/components/ChartWrapper';

// --- Helper: Format Currency ---
const formatINR = (val: number) => {
  return "₹" + val.toLocaleString('en-IN', { 
    minimumFractionDigits: 2, 
    maximumFractionDigits: 2 
  });
};

// --- Sub-component: Reset Account Dialog ---
// Since Shadcn AlertDialog might not be fully installed, we use a simple confirm-based implementation
const ResetAccountButton = () => {
  const { resetAccount, isLoading } = usePaperTradingStore();
  const { toast } = useToast();

  const handleReset = async () => {
    if (confirm("Clear all positions and reset to ₹10L? This cannot be undone.")) {
      try {
        await resetAccount();
        toast({ type: 'success', title: 'Account reset', description: 'Your paper trading account has been reset to ₹10,00,000.' });
      } catch (error: any) {
        toast({ type: 'error', title: 'Reset failed', description: error.message });
      }
    }
  };

  return (
    <Button variant="outline" size="sm" onClick={handleReset} disabled={isLoading} className="gap-2">
      <RefreshCcw className={cn("w-4 h-4", isLoading && "animate-spin")} />
      Reset Account
    </Button>
  );
};

export default function PaperTradingDashboard() {
  const { 
    portfolio, orders, isLoading, isPlacingOrder,
    fetchPortfolio, fetchOrders, placeOrder 
  } = usePaperTradingStore();
  const { toast } = useToast();

  // Local state for order form
  const [selectedTicker, setSelectedTicker] = useState("");
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [quantity, setQuantity] = useState<number>(1);
  const [orderType, setOrderType] = useState<"MARKET" | "LIMIT">("MARKET");
  const [limitPrice, setLimitPrice] = useState<number>(0);
  const [showAllOrders, setShowAllOrders] = useState(false);
  const [isOrdersOpen, setIsOrdersOpen] = useState(false);

  useEffect(() => {
    fetchPortfolio();
    fetchOrders();
  }, [fetchPortfolio, fetchOrders]);

  // Derived data
  const displayedOrders = useMemo(() => {
    return showAllOrders ? orders : orders.slice(0, 10);
  }, [orders, showAllOrders]);

  const estimatedCost = useMemo(() => {
    if (orderType === "LIMIT") return quantity * limitPrice;
    // For MARKET, we'd ideally need real-time price, but for estimate we use last known price if available
    const pos = portfolio?.positions.find(p => p.ticker === selectedTicker);
    return quantity * (pos?.current_price || 0);
  }, [quantity, limitPrice, orderType, selectedTicker, portfolio]);

  const handlePlaceOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicker) return;

    try {
      const order = await placeOrder({
        ticker: selectedTicker.toUpperCase(),
        side,
        quantity,
        order_type: orderType,
        limit_price: orderType === "LIMIT" ? limitPrice : undefined
      });

      if (order.status === "EXECUTED") {
        toast({ 
          type: 'success', 
          title: 'Order Executed', 
          description: `${order.side} ${order.quantity} ${order.ticker} executed at ${formatINR(order.executed_price || 0)}` 
        });
        setSelectedTicker("");
        setQuantity(1);
      } else {
        toast({ 
          type: 'error', 
          title: 'Order Rejected', 
          description: `Insufficient funds or position to ${side.toLowerCase()} ${quantity} ${selectedTicker}` 
        });
      }
    } catch (error: any) {
      toast({ type: 'error', title: 'Order Failed', description: error.message });
    }
  };

  const getPnLClass = (val: number) => val >= 0 ? "text-green-500" : "text-red-500";

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Stats Bar */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-slate-400 flex items-center gap-2 uppercase tracking-wider">
              <Wallet className="w-4 h-4 text-blue-400" />
              Cash Balance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono">
              {portfolio ? formatINR(portfolio.cash_balance) : "---"}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-slate-400 flex items-center gap-2 uppercase tracking-wider">
              <Briefcase className="w-4 h-4 text-purple-400" />
              Portfolio Value
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-slate-200">
              {portfolio ? formatINR(portfolio.total_current_value) : "---"}
            </div>
          </CardContent>
        </Card>

        <Card className={cn(
          "border-0",
          (portfolio?.total_pnl || 0) >= 0 ? "bg-green-900/20" : "bg-red-900/20"
        )}>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium flex items-center gap-2 uppercase tracking-wider opacity-80">
              <TrendingUp className="w-4 h-4" />
              Total P&L
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={cn("text-2xl font-bold font-mono", getPnLClass(portfolio?.total_pnl || 0))}>
              {portfolio ? `${portfolio.total_pnl >= 0 ? '+' : ''}${formatINR(portfolio.total_pnl)}` : "---"}
              <span className="text-sm ml-2 opacity-80">({portfolio?.total_pnl_pct.toFixed(2)}%)</span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-900/50 border-slate-800 flex flex-col justify-between">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-slate-400 flex items-center gap-2 uppercase tracking-wider">
              <History className="w-4 h-4 text-orange-400" />
              Total Invested
            </CardTitle>
          </CardHeader>
          <CardContent className="flex justify-between items-end">
            <div className="text-2xl font-bold font-mono text-slate-300">
              {portfolio ? formatINR(portfolio.total_invested) : "---"}
            </div>
            <ResetAccountButton />
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Positions & Chart & History */}
        <div className="lg:col-span-8 space-y-6">
          {/* Positions Table */}
          <Card className="bg-slate-900/40 border-slate-800 backdrop-blur-sm">
            <CardHeader className="border-b border-slate-800/50">
              <CardTitle className="text-lg font-semibold flex items-center gap-2">
                Open Positions
                <Badge variant="secondary" className="ml-2 bg-slate-800 text-slate-400">
                  {portfolio?.positions.length || 0}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader className="bg-slate-950/30">
                  <TableRow className="border-slate-800 hover:bg-transparent">
                    <TableHead className="text-slate-400">Ticker</TableHead>
                    <TableHead className="text-right text-slate-400">Qty</TableHead>
                    <TableHead className="text-right text-slate-400">Avg Price</TableHead>
                    <TableHead className="text-right text-slate-400">Current</TableHead>
                    <TableHead className="text-right text-slate-400">P&L</TableHead>
                    <TableHead className="text-right text-slate-400">Value</TableHead>
                    <TableHead className="text-center text-slate-400">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {!portfolio?.positions || portfolio.positions.length === 0 ? (
                    <TableRow className="hover:bg-transparent">
                      <TableCell colSpan={7} className="h-32 text-center text-slate-500 italic">
                        No open positions. Place your first trade below.
                      </TableCell>
                    </TableRow>
                  ) : (
                    portfolio.positions.map((pos) => (
                      <TableRow key={pos.ticker} className="border-slate-800 hover:bg-slate-800/20">
                        <TableCell className="font-bold text-slate-200">{pos.ticker}</TableCell>
                        <TableCell className="text-right font-mono">{pos.quantity}</TableCell>
                        <TableCell className="text-right font-mono">{pos.avg_buy_price.toFixed(2)}</TableCell>
                        <TableCell className="text-right font-mono">{pos.current_price.toFixed(2)}</TableCell>
                        <TableCell className={cn("text-right font-mono font-medium", getPnLClass(pos.pnl))}>
                          <div>{pos.pnl >= 0 ? '+' : ''}{pos.pnl.toLocaleString('en-IN')}</div>
                          <div className="text-[10px] opacity-80">({pos.pnl_pct.toFixed(2)}%)</div>
                        </TableCell>
                        <TableCell className="text-right font-mono text-slate-300">
                          {formatINR(pos.total_value)}
                        </TableCell>
                        <TableCell className="text-center">
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="h-8 text-blue-400 hover:text-blue-300 hover:bg-blue-400/10"
                            onClick={() => setSelectedTicker(pos.ticker)}
                          >
                            Trade
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* P&L Chart */}
          {portfolio && portfolio.positions.length > 0 && (
            <Card className="bg-slate-900/40 border-slate-800">
              <CardHeader>
                <CardTitle className="text-sm font-medium text-slate-400 uppercase tracking-wider">Position Performance (P&L)</CardTitle>
              </CardHeader>
              <CardContent className="h-[300px] pb-4">
                <ChartWrapper height={300}>
<ResponsiveContainer width="100%" height="100%">
                  <BarChart data={portfolio.positions}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                    <XAxis 
                      dataKey="ticker" 
                      stroke="#64748b" 
                      fontSize={12} 
                      tickLine={false} 
                      axisLine={false} 
                    />
                    <YAxis 
                      stroke="#64748b" 
                      fontSize={12} 
                      tickLine={false} 
                      axisLine={false}
                      tickFormatter={(val) => `₹${val}`}
                    />
                    <Tooltip 
                      cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                      contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
                      itemStyle={{ fontSize: '12px' }}
                      labelStyle={{ fontWeight: 'bold', marginBottom: '4px' }}
                      formatter={(value: number) => [formatINR(value), 'P&L']}
                    />
                    <Bar dataKey="pnl">
                      {portfolio.positions.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.pnl >= 0 ? '#10b981' : '#ef4444'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
</ChartWrapper>
              </CardContent>
            </Card>
          )}

          {/* Order History (Collapsible) */}
          <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-900/40">
            <button 
              onClick={() => setIsOrdersOpen(!isOrdersOpen)}
              className="w-full flex items-center justify-between p-4 bg-slate-950/50 hover:bg-slate-950 transition-colors"
            >
              <span className="font-semibold flex items-center gap-2">
                <History className="w-4 h-4 text-slate-400" />
                Order History ({orders.length})
              </span>
              {isOrdersOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
            
            {isOrdersOpen && (
              <div className="p-0 border-t border-slate-800 animate-in slide-in-from-top duration-300">
                <Table>
                  <TableHeader className="bg-slate-950/20">
                    <TableRow className="border-slate-800 hover:bg-transparent">
                      <TableHead className="text-slate-400">Time</TableHead>
                      <TableHead className="text-slate-400">Ticker</TableHead>
                      <TableHead className="text-slate-400">Side</TableHead>
                      <TableHead className="text-right text-slate-400">Qty</TableHead>
                      <TableHead className="text-right text-slate-400">Exec Price</TableHead>
                      <TableHead className="text-center text-slate-400">Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {displayedOrders.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="h-20 text-center text-slate-500">No orders yet.</TableCell>
                      </TableRow>
                    ) : (
                      displayedOrders.map((order) => (
                        <TableRow key={order.id} className="border-slate-800 text-xs">
                          <TableCell className="text-slate-500 whitespace-nowrap">
                            {new Date(order.created_at).toLocaleString('en-IN', { hour12: true })}
                          </TableCell>
                          <TableCell className="font-bold text-slate-300">{order.ticker}</TableCell>
                          <TableCell>
                            <Badge className={cn(
                              "text-[10px] font-bold px-1.5 py-0 h-5 border-0",
                              order.side === "BUY" ? "bg-blue-500/20 text-blue-400" : "bg-orange-500/20 text-orange-400"
                            )}>
                              {order.side}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right font-mono">{order.quantity}</TableCell>
                          <TableCell className="text-right font-mono">
                            {order.executed_price ? order.executed_price.toFixed(2) : "---"}
                          </TableCell>
                          <TableCell className="text-center">
                            <Badge className={cn(
                              "text-[10px] font-bold px-1.5 py-0 h-5 border-0",
                              order.status === "EXECUTED" ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                            )}>
                              {order.status}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
                {orders.length > 10 && (
                  <div className="p-3 text-center border-t border-slate-800 bg-slate-950/30">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="text-slate-400 hover:text-slate-200"
                      onClick={() => setShowAllOrders(!showAllOrders)}
                    >
                      {showAllOrders ? "Show Less" : `Show All (${orders.length})`}
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Order Form (Sticky) */}
        <div className="lg:col-span-4">
          <Card className="sticky top-24 bg-slate-900 border-slate-700 shadow-2xl overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-600 via-purple-600 to-red-600" />
            <CardHeader>
              <CardTitle className="text-xl font-bold flex items-center gap-2">
                Order Management
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handlePlaceOrder} className="space-y-6">
                {/* Side Toggle */}
                <div className="flex p-1 bg-slate-950 rounded-lg gap-1 border border-slate-800">
                  <button
                    type="button"
                    onClick={() => setSide("BUY")}
                    className={cn(
                      "flex-1 py-2 rounded-md font-bold text-sm transition-all",
                      side === "BUY" ? "bg-blue-600 text-white shadow-lg" : "text-slate-500 hover:text-slate-300"
                    )}
                  >
                    BUY
                  </button>
                  <button
                    type="button"
                    onClick={() => setSide("SELL")}
                    className={cn(
                      "flex-1 py-2 rounded-md font-bold text-sm transition-all",
                      side === "SELL" ? "bg-red-600 text-white shadow-lg" : "text-slate-500 hover:text-slate-300"
                    )}
                  >
                    SELL
                  </button>
                </div>

                {/* Inputs */}
                <div className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-400 uppercase">Ticker Symbol</label>
                    <Input 
                      placeholder="e.g. AAPL, RELIANCE.NS"
                      value={selectedTicker}
                      onChange={(e) => setSelectedTicker(e.target.value.toUpperCase())}
                      className="bg-slate-950 border-slate-800 focus:border-blue-500"
                      required
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="text-xs font-semibold text-slate-400 uppercase">Quantity</label>
                      <Input 
                        type="number"
                        min={1}
                        value={quantity}
                        onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 0))}
                        className="bg-slate-950 border-slate-800 focus:border-blue-500"
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-semibold text-slate-400 uppercase">Type</label>
                      <div className="flex bg-slate-950 rounded-md border border-slate-800 h-10 p-0.5">
                        <button
                          type="button"
                          onClick={() => setOrderType("MARKET")}
                          className={cn(
                            "flex-1 text-[10px] font-bold rounded-sm uppercase transition-colors",
                            orderType === "MARKET" ? "bg-slate-800 text-white" : "text-slate-500"
                          )}
                        >
                          Market
                        </button>
                        <button
                          type="button"
                          onClick={() => setOrderType("LIMIT")}
                          className={cn(
                            "flex-1 text-[10px] font-bold rounded-sm uppercase transition-colors",
                            orderType === "LIMIT" ? "bg-slate-800 text-white" : "text-slate-500"
                          )}
                        >
                          Limit
                        </button>
                      </div>
                    </div>
                  </div>

                  {orderType === "LIMIT" && (
                    <div className="space-y-2 animate-in fade-in slide-in-from-top-2">
                      <label className="text-xs font-semibold text-slate-400 uppercase">Limit Price</label>
                      <Input 
                        type="number"
                        step="0.05"
                        value={limitPrice}
                        onChange={(e) => setLimitPrice(parseFloat(e.target.value) || 0)}
                        className="bg-slate-950 border-slate-800 focus:border-blue-500"
                        required
                      />
                    </div>
                  )}
                </div>

                {/* Estimation Info */}
                <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800 space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400">Estimated {side === "BUY" ? "Cost" : "Proceeds"}</span>
                    <span className="font-mono font-bold text-slate-200">{formatINR(estimatedCost)}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400">Available Cash</span>
                    <span className="font-mono font-bold text-slate-200">
                      {portfolio ? formatINR(portfolio.cash_balance) : "---"}
                    </span>
                  </div>
                  {side === "BUY" && portfolio && estimatedCost > portfolio.cash_balance && (
                    <div className="flex items-center gap-2 text-[10px] text-red-400 bg-red-400/10 p-2 rounded-lg mt-2">
                      <AlertCircle className="w-3 h-3" />
                      Warning: Insufficient cash balance
                    </div>
                  )}
                </div>

                <Button 
                  type="submit" 
                  className={cn(
                    "w-full h-12 text-lg font-bold shadow-xl transition-all active:scale-[0.98]",
                    side === "BUY" ? "bg-blue-600 hover:bg-blue-500" : "bg-red-600 hover:bg-red-500"
                  )}
                  disabled={isPlacingOrder || !selectedTicker}
                >
                  {isPlacingOrder ? (
                    <>
                      <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                      PLACING...
                    </>
                  ) : (
                    `PLACE ${side} ORDER`
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
