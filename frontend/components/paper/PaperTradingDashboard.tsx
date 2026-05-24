"use client";

import React, { useEffect, useState } from 'react';
import { usePaperStore } from '@/store/paperStore';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { 
  Wallet, 
  ArrowUpRight, 
  ArrowDownRight, 
  History, 
  RefreshCcw, 
  TrendingUp, 
  BarChart3,
  Loader2
} from 'lucide-react';

const formatCurrency = (val: number) => {
  return "₹" + val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

export default function PaperTradingDashboard() {
  const { 
    portfolio, orders, isLoading, isPlacingOrder,
    fetchPortfolio, fetchOrders, placeOrder, resetAccount 
  } = usePaperStore();

  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");

  useEffect(() => {
    fetchPortfolio();
    fetchOrders();
  }, [fetchPortfolio, fetchOrders]);

  const handleOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker) return;
    
    await placeOrder({
      ticker: ticker.toUpperCase(),
      quantity: quantity,
      side: side,
      order_type: "MARKET"
    });
    
    setTicker("");
    setQuantity(1);
  };

  const getPnLColor = (val: number) => val >= 0 ? "text-green-500 font-bold" : "text-red-500 font-bold";

  return (
    <div className="space-y-6 p-4">
      {/* Top Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Wallet className="w-4 h-4 text-blue-500" />
              Cash Balance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{portfolio ? formatCurrency(portfolio.cash_balance) : '...'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-purple-500" />
              Portfolio Value
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{portfolio ? formatCurrency(portfolio.total_current_value) : '...'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-green-500" />
              Total P&L
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getPnLColor(portfolio?.total_pnl || 0)}`}>
              {portfolio ? formatCurrency(portfolio.total_pnl) : '...'}
              <span className="text-sm ml-2">({portfolio?.total_pnl_pct.toFixed(2)}%)</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <RefreshCcw className="w-4 h-4 text-orange-500" />
              Actions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Button variant="outline" size="sm" onClick={() => {
              if (confirm("Reset account to ₹10 Lakh? This will delete all positions.")) {
                resetAccount();
              }
            }}>
              Reset Account
            </Button>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left - Trading Terminal */}
        <Card className="lg:col-span-4 h-fit">
          <CardHeader>
            <CardTitle>Trading Terminal</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleOrder} className="space-y-4">
              <div className="flex gap-2 p-1 bg-muted rounded-md">
                <Button 
                  type="button"
                  variant={side === "BUY" ? "default" : "ghost"}
                  className="flex-1"
                  onClick={() => setSide("BUY")}
                >
                  BUY
                </Button>
                <Button 
                  type="button"
                  variant={side === "SELL" ? "destructive" : "ghost"}
                  className="flex-1"
                  onClick={() => setSide("SELL")}
                >
                  SELL
                </Button>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Ticker (NSE)</label>
                <Input 
                  placeholder="e.g. RELIANCE.NS" 
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Quantity</label>
                <Input 
                  type="number" 
                  min="1"
                  value={quantity}
                  onChange={(e) => setQuantity(parseInt(e.target.value) || 0)}
                  required
                />
              </div>

              <Button 
                type="submit" 
                className="w-full" 
                disabled={isPlacingOrder || !ticker}
              >
                {isPlacingOrder ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : "Place Order"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Right - Tabs for Positions and Orders */}
        <Card className="lg:col-span-8">
          <CardContent className="pt-6">
            <Tabs defaultValue="positions">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="positions">Current Positions</TabsTrigger>
                <TabsTrigger value="orders">Order History</TabsTrigger>
              </TabsList>
              
              <TabsContent value="positions" className="pt-4">
                <div className="rounded-md border overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Ticker</TableHead>
                        <TableHead className="text-right">Qty</TableHead>
                        <TableHead className="text-right">Avg Price</TableHead>
                        <TableHead className="text-right">Market Price</TableHead>
                        <TableHead className="text-right">PnL</TableHead>
                        <TableHead className="text-right">Value</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {portfolio?.positions.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                            No active positions.
                          </TableCell>
                        </TableRow>
                      ) : (
                        portfolio?.positions.map((pos) => (
                          <TableRow key={pos.ticker}>
                            <TableCell className="font-bold">{pos.ticker}</TableCell>
                            <TableCell className="text-right font-mono">{pos.quantity}</TableCell>
                            <TableCell className="text-right font-mono">{pos.avg_buy_price.toFixed(2)}</TableCell>
                            <TableCell className="text-right font-mono">{pos.current_price.toFixed(2)}</TableCell>
                            <TableCell className={`text-right ${getPnLColor(pos.pnl)}`}>
                              {pos.pnl > 0 ? '+' : ''}{pos.pnl.toFixed(2)} ({pos.pnl_pct.toFixed(2)}%)
                            </TableCell>
                            <TableCell className="text-right font-mono">{formatCurrency(pos.total_value)}</TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </TabsContent>

              <TabsContent value="orders" className="pt-4">
                <div className="rounded-md border overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Time</TableHead>
                        <TableHead>Ticker</TableHead>
                        <TableHead>Side</TableHead>
                        <TableHead className="text-right">Qty</TableHead>
                        <TableHead className="text-right">Price</TableHead>
                        <TableHead>Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {orders.map((order) => (
                        <TableRow key={order.id}>
                          <TableCell className="text-xs text-muted-foreground">
                            {new Date(order.created_at).toLocaleString()}
                          </TableCell>
                          <TableCell className="font-medium">{order.ticker}</TableCell>
                          <TableCell>
                            <Badge variant={order.side === "BUY" ? "outline" : "secondary"}>
                              {order.side}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right font-mono">{order.quantity}</TableCell>
                          <TableCell className="text-right font-mono">
                            {order.executed_price?.toFixed(2) || '-'}
                          </TableCell>
                          <TableCell>
                            <Badge variant={order.status === "EXECUTED" ? "default" : "destructive"}>
                              {order.status}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
