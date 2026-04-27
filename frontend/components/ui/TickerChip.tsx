"use client";

import React from 'react';
import { X, TrendingUp, TrendingDown } from 'lucide-react';
import { cn } from '@/lib/utils';

interface TickerChipProps {
  ticker: string;
  exchange?: string;
  price?: number;
  change?: number;
  onClear?: () => void;
  className?: string;
}

export const TickerChip: React.FC<TickerChipProps> = ({
  ticker,
  exchange,
  price,
  change,
  onClear,
  className
}) => {
  const isPositive = change && change >= 0;

  return (
    <div className={cn(
      "flex items-center gap-3 bg-surface border border-white/10 rounded-full pl-3 pr-1 py-1 text-sm group transition-all hover:border-accent/50",
      className
    )}>
      <span className="text-gray-400 text-xs font-medium uppercase">Analyzing:</span>
      <div className="flex items-center gap-2">
        <span className="font-mono font-bold text-white tracking-wider">{ticker}</span>
        {exchange && (
          <span className="px-1.5 py-0.5 rounded bg-white/5 text-[10px] text-gray-500 font-bold">
            {exchange}
          </span>
        )}
      </div>
      
      {(price !== undefined || change !== undefined) && (
        <div className="flex items-center gap-2 border-l border-white/5 pl-2">
          {price !== undefined && (
            <span className="font-mono font-medium text-white">${price.toLocaleString()}</span>
          )}
          {change !== undefined && (
            <div className={cn(
              "flex items-center gap-0.5 font-mono text-xs font-bold",
              isPositive ? "text-green-500" : "text-red-500"
            )}>
              {isPositive ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
              {Math.abs(change).toFixed(2)}%
            </div>
          )}
        </div>
      )}

      {onClear && (
        <button 
          onClick={onClear}
          className="ml-1 p-1 rounded-full hover:bg-white/10 text-gray-500 hover:text-white transition-colors"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
};
