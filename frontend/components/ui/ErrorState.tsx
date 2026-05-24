import React from 'react';
import { Button } from './button'; // Assuming shadcn ui button exists
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
    title?: string;
    message?: string;
    onRetry?: () => void;
    icon?: React.ReactNode;
}

export function ErrorState({ 
    title = 'Something went wrong', 
    message = 'We encountered an error loading this data. Please try again.', 
    onRetry,
    icon = <AlertCircle className="w-10 h-10 text-red-500" />
}: ErrorStateProps) {
    return (
        <div className="flex flex-col items-center justify-center p-8 space-y-4 text-center border rounded-xl bg-slate-50/50 dark:bg-slate-900/50">
            <div className="p-3 bg-red-100 dark:bg-red-900/20 rounded-full">
                {icon}
            </div>
            <div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-sm">
                    {message}
                </p>
            </div>
            {onRetry && (
                <Button 
                    onClick={onRetry} 
                    variant="outline" 
                    className="mt-4 flex items-center space-x-2"
                >
                    <RefreshCw className="w-4 h-4" />
                    <span>Try Again</span>
                </Button>
            )}
        </div>
    );
}
