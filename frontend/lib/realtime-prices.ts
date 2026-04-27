import { useEffect, useState, useRef } from 'react';
import { createClient } from './supabase';

export function useRealtimePrices(initialTickers: string[]) {
  const [prices, setPrices] = useState<Record<string, { value: number, change: number }>>({});
  const supabase = createClient();
  const tickersRef = useRef<string[]>(initialTickers);

  useEffect(() => {
    tickersRef.current = initialTickers;
  }, [initialTickers]);

  useEffect(() => {
    if (initialTickers.length === 0) return;

    const channel = supabase
      .channel('live_ticker_updates')
      .on('postgres_changes', { 
        event: 'UPDATE', 
        schema: 'public', 
        table: 'market_cache' 
      }, (payload) => {
        const data = payload.new as any;
        if (tickersRef.current.includes(data.symbol)) {
          setPrices(prev => ({
            ...prev,
            [data.symbol]: {
              value: data.last_price,
              change: data.change_percent
            }
          }));
        }
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [initialTickers]);

  return prices;
}
