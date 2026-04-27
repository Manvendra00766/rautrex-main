"use client";

import React, { createContext, useContext, useState, useCallback } from 'react';
import { X, CheckCircle, AlertTriangle, AlertCircle, Info, BrainCircuit, Activity, ShieldAlert, Newspaper, Terminal } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

type ToastType = 'success' | 'error' | 'warning' | 'info' | 'signal' | 'price_alert' | 'backtest' | 'portfolio' | 'system';

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
}

interface ToastContextType {
  toast: (props: { type?: ToastType; title: string; description?: string }) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used within ToastProvider');
  return context;
};

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback(({ type = 'info', title, description }: { type?: ToastType; title: string; description?: string }) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => {
        const next = [...prev, { id, type, title, description }];
        if (next.length > 5) return next.slice(next.length - 5);
        return next;
    });
    
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const getToastStyle = (type: ToastType) => {
    switch (type) {
      case 'success': return 'bg-green-500/10 border-green-500/20 text-green-500';
      case 'error': return 'bg-red-500/10 border-red-500/20 text-red-500';
      case 'warning': return 'bg-amber-500/10 border-amber-500/20 text-amber-500';
      case 'info': return 'bg-blue-500/10 border-blue-500/20 text-blue-500';
      case 'signal': return 'bg-cyan-500/10 border-cyan-500/20 text-cyan-400';
      case 'price_alert': return 'bg-green-500/10 border-green-500/20 text-green-400';
      case 'backtest': return 'bg-amber-500/10 border-amber-500/20 text-amber-400';
      case 'portfolio': return 'bg-purple-500/10 border-purple-500/20 text-purple-400';
      case 'system': return 'bg-white/5 border-white/10 text-gray-400';
      default: return 'bg-white/5 border-white/10 text-white';
    }
  };

  const getToastIcon = (type: ToastType) => {
    switch (type) {
      case 'success': return <CheckCircle size={18} />;
      case 'error': return <AlertCircle size={18} />;
      case 'warning': return <AlertTriangle size={18} />;
      case 'info': return <Info size={18} />;
      case 'signal': return <BrainCircuit size={18} />;
      case 'price_alert': return <Activity size={18} />;
      case 'backtest': return <Terminal size={18} />;
      case 'portfolio': return <ShieldAlert size={18} />;
      case 'system': return <Newspaper size={18} />;
      default: return <Info size={18} />;
    }
  };

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-6 right-6 z-[200] flex flex-col gap-3 pointer-events-none">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, x: 20, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 20, scale: 0.95 }}
              className="pointer-events-auto"
            >
              <div className={`
                w-[340px] p-4 rounded-2xl border shadow-2xl backdrop-blur-xl flex gap-3 relative overflow-hidden group
                ${getToastStyle(t.type)}
              `}>
                <div className="absolute top-0 left-0 bottom-0 w-1 bg-current opacity-30" />
                <div className="shrink-0 mt-0.5 opacity-80">
                  {getToastIcon(t.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-bold text-sm leading-tight text-white">{t.title}</h4>
                  {t.description && <p className="text-xs mt-1 text-gray-400 leading-relaxed line-clamp-2">{t.description}</p>}
                </div>
                <button 
                  onClick={() => removeToast(t.id)}
                  className="shrink-0 h-6 w-6 flex items-center justify-center hover:bg-white/10 rounded-lg transition-colors"
                >
                  <X size={14} className="text-white/40 group-hover:text-white" />
                </button>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
};
