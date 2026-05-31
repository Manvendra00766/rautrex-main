import React, { useEffect, useRef, useState } from 'react';

export default function ChartWrapper({ children, height = 300 }: { children: React.ReactNode, height?: number }) {
  const [mounted, setMounted] = useState(false);
  const [ready, setReady] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (!mounted || !containerRef.current) return;

    const el = containerRef.current;
    const checkReady = () => {
      const rect = el.getBoundingClientRect();
      setReady(rect.width > 0 && rect.height > 0);
    };

    checkReady();

    const observer = new ResizeObserver(() => checkReady());
    observer.observe(el);
    return () => observer.disconnect();
  }, [mounted]);
  
  if (!mounted || !ready) {
    return (
      <div
        ref={containerRef}
        style={{ width: '100%', height, minHeight: height, minWidth: 0, background: 'rgba(255,255,255,0.03)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#666', fontSize: 13 }}
      >
        Loading chart...
      </div>
    );
  }
  
  return (
    <div ref={containerRef} style={{ width: '100%', height, minHeight: height, minWidth: 0 }}>
      {children}
    </div>
  );
}
