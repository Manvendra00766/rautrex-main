"use client"

import React from 'react'
import ChartWrapper from '@/components/ChartWrapper';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, 
  ResponsiveContainer, Cell 
} from 'recharts'

interface ShareableFCFChartProps {
  projected_fcfs: number[]
  projection_years: number
}

export default function ShareableFCFChart({ projected_fcfs, projection_years }: ShareableFCFChartProps) {
  const data = projected_fcfs.map((fcf, i) => ({ 
    year: `Year ${i + 1}`, 
    fcf 
  }));

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(val) + ' Cr';
  };

  return (
    <div className="h-[300px] w-full mt-4">
      <ChartWrapper height={300}>
<ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
          <XAxis dataKey="year" stroke="#666" fontSize={10} axisLine={false} tickLine={false} />
          <YAxis stroke="#666" fontSize={10} axisLine={false} tickLine={false} tickFormatter={v => `₹${v}`} />
          <RechartsTooltip 
            contentStyle={{ backgroundColor: '#0d0d14', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
            formatter={(value: any) => [formatCurrency(value), 'Projected FCF']}
          />
          <Bar dataKey="fcf" radius={[6, 6, 0, 0]}>
            {projected_fcfs.map((_, index) => (
              <Cell 
                key={`cell-${index}`} 
                fill={index === projected_fcfs.length - 1 ? '#00d4ff' : '#00d4ff40'} 
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
</ChartWrapper>
    </div>
  );
}
