"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

interface SandboxContextType {
  isSandbox: boolean;
  enterSandbox: () => void;
  exitSandbox: () => void;
  exitTrigger: () => void;
}

const SandboxContext = createContext<SandboxContextType | undefined>(undefined);

export function SandboxProvider({ children }: { children: React.ReactNode }) {
  const [isSandbox, setIsSandbox] = useState<boolean>(false);

  // Load initial state on mount in a SSR-safe manner
  useEffect(() => {
    const stored = localStorage.getItem("rautrex_sandbox_mode");
    setIsSandbox(stored === "true");
  }, []);

  const enterSandbox = () => {
    localStorage.setItem("rautrex_sandbox_mode", "true");
    setIsSandbox(true);
    // Dispatch a custom event to alert other listening hooks
    window.dispatchEvent(new Event("rautrex_sandbox_change"));
  };

  const exitSandbox = () => {
    localStorage.setItem("rautrex_sandbox_mode", "false");
    setIsSandbox(false);
    window.dispatchEvent(new Event("rautrex_sandbox_change"));
  };

  const exitTrigger = () => {
    if (isSandbox) {
      exitSandbox();
    }
  };

  return (
    <SandboxContext.Provider value={{ isSandbox, enterSandbox, exitSandbox, exitTrigger }}>
      {children}
    </SandboxContext.Provider>
  );
}

export function useSandbox() {
  const context = useContext(SandboxContext);
  if (context === undefined) {
    throw new Error("useSandbox must be used within a SandboxProvider");
  }
  return context;
}
