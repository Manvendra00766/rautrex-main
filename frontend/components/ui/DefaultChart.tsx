"use client";

import React from 'react';
import { ResponsiveContainer, ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid } from 'recharts';
import { useIsMobile } from '@/lib/hooks';
import ChartWrapper from '@/components/ChartWrapper';

const sampleData = Array.from({ length: 20 }, (_, i) => ({
  time: i,
  value: 100 + Math.sin(i / 2) * 20 + i * 2,
  secondary: 90 + Math.cos(i / 2) * 10 + i * 1.5,
}));

export const DefaultChart = () => {
  const isMobile = useIsMobile();
  
  return (
    <div className="w-full h-full bg-surface rounded-2xl p-4 md:p-6 relative">
      <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
        <div className="bg-surface/60 backdrop-blur-md px-4 py-2 rounded-full border border-border text-[9px] md:text-xs font-bold text-muted tracking-wider">
          SAMPLE DATA — ENTER PARAMETERS TO RUN ANALYSIS
        </div>
      </div>
      <div className="opacity-30 w-full h-[200px] md:h-full">
        <ChartWrapper height={300}>
<ResponsiveContainer width="100%" height={isMobile ? 200 : "100%"}>
          <ComposedChart data={sampleData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis dataKey="time" hide />
            <YAxis hide />
            <Line 
              type="monotone" 
              dataKey="value" 
              stroke="var(--accent-teal)" 
              strokeWidth={2} 
              dot={false} 
              isAnimationActive={false}
            />
            <Area 
              type="monotone" 
              dataKey="secondary" 
              fill="#7c3aed" 
              stroke="#7c3aed" 
              fillOpacity={0.15} 
              strokeWidth={2}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
</ChartWrapper>
      </div>
    </div>
  );
};
