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

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';
    const socket = new WebSocket(`${wsUrl}/${user.id}`);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log('Alert WebSocket Connected');
      // Subscribe to user specific channel if needed, 
      // but backend manager handles direct user broadcasting in this case
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
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

    return () => {
      socket.close();
    };
  }, [user, updateAlertTriggered]);

  return socketRef.current;
}
