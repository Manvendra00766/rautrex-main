'use client';

import React, { useState, useEffect } from 'react';
import { useAlertsStore } from '@/store/alertsStore';
import { useAlertSocket } from '@/lib/useAlertSocket';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { 
  Bell, 
  Plus, 
  Trash2, 
  TrendingUp, 
  TrendingDown, 
  AlertCircle,
  Loader2,
  CheckCircle2
} from 'lucide-react';

export default function AlertsPage() {
  useAlertSocket(); // Initialize WebSocket listener
  const { alerts, loading, error, fetchAlerts, createAlert, deleteAlert } = useAlertsStore();
  
  const [ticker, setTicker] = useState('');
  const [condition, setCondition] = useState<'above' | 'below'>('above');
  const [targetPrice, setTargetPrice] = useState('');

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker || !targetPrice) return;
    
    await createAlert({
      ticker: ticker.toUpperCase(),
      condition,
      target_price: parseFloat(targetPrice)
    });
    
    setTicker('');
    setTargetPrice('');
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Price Alerts</h1>
        <p className="text-muted-foreground">
          Set targets and get notified in real-time when stock prices cross your thresholds.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Creation Form */}
        <Card className="lg:col-span-1 h-fit">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Plus className="w-5 h-5 text-primary" /> Create New Alert
            </CardTitle>
            <CardDescription>Configure your price trigger</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="ticker">Stock Symbol</Label>
                <Input 
                  id="ticker"
                  placeholder="e.g. RELIANCE.NS" 
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label>Condition</Label>
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    type="button"
                    variant={condition === 'above' ? 'default' : 'outline'}
                    onClick={() => setCondition('above')}
                    className="w-full"
                  >
                    <TrendingUp className="w-4 h-4 mr-2" /> Above
                  </Button>
                  <Button
                    type="button"
                    variant={condition === 'below' ? 'default' : 'outline'}
                    onClick={() => setCondition('below')}
                    className="w-full"
                  >
                    <TrendingDown className="w-4 h-4 mr-2" /> Below
                  </Button>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="target">Target Price (INR)</Label>
                <Input 
                  id="target"
                  type="number"
                  step="0.01"
                  placeholder="0.00" 
                  value={targetPrice}
                  onChange={(e) => setTargetPrice(e.target.value)}
                  required
                />
              </div>

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Bell className="w-4 h-4 mr-2" />}
                Set Alert
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Alerts List */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Active & Past Alerts</CardTitle>
            <CardDescription>Monitor your triggers</CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <div className="mb-4 p-3 bg-destructive/10 text-destructive text-sm rounded-md flex items-center gap-2">
                <AlertCircle className="w-4 h-4" /> {error}
              </div>
            )}

            {alerts.length > 0 ? (
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Ticker</TableHead>
                      <TableHead>Condition</TableHead>
                      <TableHead className="text-right">Target Price</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Created At</TableHead>
                      <TableHead className="text-right">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {alerts.map((alert) => (
                      <TableRow key={alert.id} className={alert.is_triggered ? 'bg-muted/30' : ''}>
                        <TableCell className="font-bold">{alert.ticker}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {alert.condition === 'above' ? (
                              <TrendingUp className="w-4 h-4 text-green-500" />
                            ) : (
                              <TrendingDown className="w-4 h-4 text-red-500" />
                            )}
                            <span className="capitalize">{alert.condition}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          ₹{alert.target_price.toLocaleString()}
                        </TableCell>
                        <TableCell>
                          {alert.is_triggered ? (
                            <Badge variant="secondary" className="bg-green-100 text-green-800 hover:bg-green-100 flex items-center gap-1 w-fit">
                              <CheckCircle2 className="w-3 h-3" /> Triggered
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="flex items-center gap-1 w-fit">
                              <Loader2 className="w-3 h-3 animate-spin" /> Active
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                          {formatDate(alert.created_at)}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            className="text-destructive hover:text-destructive hover:bg-destructive/10"
                            onClick={() => deleteAlert(alert.id)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Bell className="w-12 h-12 text-muted-foreground mb-4 opacity-20" />
                <h3 className="text-lg font-semibold">No alerts set</h3>
                <p className="text-muted-foreground">Set your first price alert to start monitoring.</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
