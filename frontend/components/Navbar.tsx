"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { useAuthStore } from "@/lib/auth-store";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Menu, X } from "lucide-react";

export default function Navbar() {
  const { user } = useAuthStore();
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const navLinks = [
    { name: "Features", href: "#features" },
    { name: "How It Works", href: "#how-it-works" },
    { name: "About", href: "#about" },
  ];

  return (
    <nav
      className={cn(
        "fixed top-0 left-0 right-0 z-[100] transition-all duration-300 px-6 h-20 flex items-center justify-between",
        scrolled ? "bg-background/80 backdrop-blur-xl border-b border-border h-16" : "bg-transparent"
      )}
    >
      {/* Logo */}
      <Link href="/" className="flex items-center">
        <span className="font-mono font-black text-2xl tracking-tighter text-foreground">RAUTREX</span>
      </Link>

      {/* Desktop Links */}
      <div className="hidden md:flex items-center gap-8">
        {navLinks.map((link) => (
          <Link
            key={link.name}
            href={link.href}
            className="text-sm font-medium text-text-muted hover:text-foreground transition-colors"
          >
            {link.name}
          </Link>
        ))}
      </div>

      {/* Auth Buttons */}
      <div className="hidden md:flex items-center gap-4">
        {user ? (
          <Link href="/dashboard">
            <Button className="bg-accent hover:bg-accent/90 text-foreground font-bold px-6 rounded-full transition-all hover:scale-105 active:scale-95">
              DASHBOARD
            </Button>
          </Link>
        ) : (
          <>
            <Link href="/login">
              <Button variant="ghost" className="text-text-muted hover:text-foreground font-bold">
                LOGIN
              </Button>
            </Link>
            <Link href="/signup">
              <Button className="bg-accent hover:bg-accent/90 text-foreground font-bold px-6 rounded-full transition-all hover:scale-105 active:scale-95">
                GET STARTED
              </Button>
            </Link>
          </>
        )}
      </div>

      {/* Mobile Toggle */}
      <button className="md:hidden text-foreground" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
        {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="absolute top-full left-0 right-0 bg-surface border-b border-border p-6 flex flex-col gap-6 md:hidden animate-in slide-in-from-top duration-300">
          {navLinks.map((link) => (
            <Link
              key={link.name}
              href={link.href}
              className="text-lg font-medium text-text-muted"
              onClick={() => setMobileMenuOpen(false)}
            >
              {link.name}
            </Link>
          ))}
          <div className="flex flex-col gap-3 pt-4 border-t border-border">
            {user ? (
               <Link href="/dashboard" onClick={() => setMobileMenuOpen(false)}>
                  <Button className="w-full bg-accent text-foreground font-bold">DASHBOARD</Button>
               </Link>
            ) : (
              <>
                <Link href="/login" onClick={() => setMobileMenuOpen(false)}>
                  <Button variant="outline" className="w-full border-border text-foreground">LOGIN</Button>
                </Link>
                <Link href="/signup" onClick={() => setMobileMenuOpen(false)}>
                  <Button className="w-full bg-accent text-foreground font-bold">GET STARTED</Button>
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
