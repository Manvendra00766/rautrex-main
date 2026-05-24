import { useState, useEffect, useRef, useCallback } from 'react';

interface MarketData {
    ticker: string;
    price: number;
    timestamp?: string;
}

interface UseRealtimeOptions {
    fallbackData?: Record<string, number>;
    autoReconnect?: boolean;
    maxRetries?: number;
}

export function useRealtimeMarket(tickers: string[], options: UseRealtimeOptions = {}) {
    const { fallbackData = {}, autoReconnect = true, maxRetries = 5 } = options;
    const [prices, setPrices] = useState<Record<string, number>>(fallbackData);
    const [isConnected, setIsConnected] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    
    const wsRef = useRef<WebSocket | null>(null);
    const retryCountRef = useRef(0);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    
    // Stale data tracking
    const lastUpdateRef = useRef<Record<string, number>>({});

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;
        
        try {
            const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/stream';
            const ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                setIsConnected(true);
                setError(null);
                retryCountRef.current = 0;
                
                // Subscribe to required tickers
                tickers.forEach(ticker => {
                    ws.send(JSON.stringify({ type: 'subscribe', channel: `ticker:${ticker}` }));
                });
            };

            ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.type === 'ping') {
                        ws.send(JSON.stringify({ type: 'pong' }));
                    } else if (msg.type === 'market_update' && msg.ticker && msg.price) {
                        setPrices(prev => ({ ...prev, [msg.ticker]: msg.price }));
                        lastUpdateRef.current[msg.ticker] = Date.now();
                    }
                } catch (err) {
                    console.warn('Failed to parse WS message', err);
                }
            };

            ws.onclose = () => {
                setIsConnected(false);
                wsRef.current = null;
                
                if (autoReconnect && retryCountRef.current < maxRetries) {
                    const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30000);
                    retryCountRef.current += 1;
                    reconnectTimeoutRef.current = setTimeout(connect, delay);
                }
            };

            ws.onerror = (err) => {
                console.error('WebSocket Error:', err);
                setError(new Error('WebSocket connection failed'));
            };

            wsRef.current = ws;
        } catch (err) {
            setError(err instanceof Error ? err : new Error('Unknown error connecting to WebSocket'));
        }
    }, [tickers, autoReconnect, maxRetries]);

    useEffect(() => {
        connect();
        
        return () => {
            if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
            if (wsRef.current) {
                // Cleanup subscriptions before closing
                if (wsRef.current.readyState === WebSocket.OPEN) {
                    tickers.forEach(ticker => {
                        wsRef.current?.send(JSON.stringify({ type: 'unsubscribe', channel: `ticker:${ticker}` }));
                    });
                }
                wsRef.current.close();
            }
        };
    }, [connect, tickers]);

    // Derived state: check if data is stale (e.g. > 60s old)
    const isStale = (ticker: string) => {
        const lastUpdate = lastUpdateRef.current[ticker];
        if (!lastUpdate) return true;
        return Date.now() - lastUpdate > 60000; 
    };

    return { prices, isConnected, error, isStale, reconnect: connect };
}
