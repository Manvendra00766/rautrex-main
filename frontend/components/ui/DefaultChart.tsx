"use client";

import React from 'react';
import { ResponsiveContainer, ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid } from 'recharts';
import { useIsMobile } from '@/lib/hooks';

const sampleData = Array.from({ length: 20 }, (_, i) => ({
  time: i,
  value: 100 + Math.sin(i / 2) * 20 + i * 2,
  secondary: 90 + Math.cos(i / 2) * 10 + i * 1.5,
}));

export const DefaultChart = () => {
  const isMobile = useIsMobile();
  
  return (
    <div className="w-full h-full bg-[#0d0d14] rounded-2xl p-4 md:p-6 relative">
      <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
        <div className="bg-black/60 backdrop-blur-md px-4 py-2 rounded-full border border-white/10 text-[9px] md:text-xs font-bold text-gray-400 tracking-wider">
          SAMPLE DATA — ENTER PARAMETERS TO RUN ANALYSIS
        </div>
      </div>
      <div className="opacity-30 w-full h-[200px] md:h-full">
        <ResponsiveContainer width="100%" height={isMobile ? 200 : "100%"}>
          <ComposedChart data={sampleData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
            <XAxis dataKey="time" hide />
            <YAxis hide />
            <Line 
              type="monotone" 
              dataKey="value" 
              stroke="#00d4ff" 
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
      </div>
    </div>
  );
};
