import React from "react";
import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import AuthProvider from "@/components/auth-provider";
import { ToastProvider } from "@/components/ui/Toast";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const jetbrainsMono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains" });

export const metadata: Metadata = {
  title: "RAUTREX | Global Quant Terminal",
  description: "Bloomberg-grade quant terminal for global retail traders.",
  icons: {
    icon: '/logo.png',
    shortcut: '/logo.png',
    apple: '/logo.png',
  }
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans bg-background text-foreground antialiased flex h-screen overflow-hidden`}>
        <ToastProvider>
          <AuthProvider>
            {children}
          </AuthProvider>
        </ToastProvider>
      </body>
    </html>
  );
}
