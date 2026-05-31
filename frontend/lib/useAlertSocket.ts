'use client';

import { useEffect, useRef } from 'react';
import { useAlertsStore } from '@/store/alertsStore';
import { useAuthStore } from '@/lib/auth-store';
import { useToast } from '@/components/ui/Toast';

export function useAlertSocket() {
  const { user } = useAuthStore();
  const { toast } = useToast();
  const updateAlertTriggered = useAlertsStore((state) => state.updateAlertTriggered);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!user) return;

    // Use the correct WebSocket endpoint: /ws/stream with client_id query param
    const baseApi = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    // Derive WebSocket base from API URL (strip /api/v1 and swap http→ws)
    const httpBase = baseApi.replace(/\/api\/v1\/?$/, '');
    const wsBase = httpBase.replace(/^http/, 'ws');
    const wsUrl = `${wsBase}/ws/stream?client_id=${user.id}`;

    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log('Alert WebSocket Connected to', wsUrl);
      // Subscribe to market channel to receive live price updates
      socket.send(JSON.stringify({ type: 'subscribe', channel: 'market' }));
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'ping') {
          // Respond to heartbeat pings to keep connection alive
          socket.send(JSON.stringify({ type: 'pong' }));
          return;
        }

        if (data.type === 'ALERT_TRIGGERED') {
          // Play sound
          const audio = new Audio('/sounds/alert.mp3');
          audio.play().catch(() => {}); // Ignore if blocked by browser

          // Show Toast
          toast({
            title: `🚨 Price Alert Triggered: ${data.symbol}`,
            description: `${data.symbol} hit ${data.condition} ${data.target_price}. Current: ${data.current_price}`,
            type: 'price_alert',
          });

          // Update local store state
          updateAlertTriggered(data.symbol, data.target_price);
        }
      } catch (err) {
        console.error('WS Message Parse Error:', err);
      }
    };

    socket.onclose = () => {
      console.log('Alert WebSocket Disconnected');
    };

    socket.onerror = (err) => {
      console.error('Alert WebSocket Error:', err);
    };

    return () => {
      socket.close();
    };
  }, [user, updateAlertTriggered]);

  return socketRef.current;
}
