"use client";

import React from 'react';
import { AlertTriangle, Database } from 'lucide-react';
import { Button } from './button';

interface ErrorStateProps {
  type?: 'error' | 'empty';
  onRetry?: () => void;
  message?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({ 
  type = 'error', 
  onRetry, 
  message 
}) => {
  return (
    <div className="w-full h-full flex flex-col items-center justify-center bg-[#0d0d14] rounded-2xl p-8 text-center space-y-4">
      {type === 'error' ? (
        <>
          <div className="p-4 rounded-full bg-red-500/10 text-red-500">
            <AlertTriangle size={32} />
          </div>
          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-white">Unable to load data</h3>
            <p className="text-sm text-gray-400 max-w-xs mx-auto">
              {message || "We encountered an issue while fetching the requested analysis."}
            </p>
          </div>
          {onRetry && (
            <Button onClick={onRetry} variant="outline" className="mt-2 border-white/10 hover:bg-white/5">
              Retry Connection
            </Button>
          )}
        </>
      ) : (
        <>
          <div className="p-4 rounded-full bg-blue-500/10 text-blue-400">
            <Database size={32} />
          </div>
          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-white">No data available</h3>
            <p className="text-sm text-gray-400 max-w-xs mx-auto">
              {message || "No data available for this period or ticker combination."}
            </p>
          </div>
        </>
      )}
    </div>
  );
};
