"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { useAuthStore } from "@/lib/auth-store";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Menu, X } from "lucide-react";
import { motion } from "framer-motion";

export default function Navbar() {
  const { user } = useAuthStore();
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const [activeSection, setActiveSection] = useState("");

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
      
      const sections = ["features", "how-it-works", "why-us", "roadmap", "about"];
      let currentActive = "";
      for (const section of sections) {
        const el = document.getElementById(section);
        if (el) {
          const rect = el.getBoundingClientRect();
          if (rect.top <= 160 && rect.bottom >= 160) {
            currentActive = section;
            break;
          }
        }
      }
      setActiveSection(currentActive);
    };
    
    // Run once on mount
    handleScroll();
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const navLinks = [
    { name: "Features", href: "/#features" },
    { name: "How It Works", href: "/#how-it-works" },
    { name: "Why Rautrex", href: "/#why-us" },
    { name: "Roadmap", href: "/#roadmap" },
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
            className={cn(
              "text-sm font-medium transition-colors relative py-1",
              activeSection === link.href.substring(1)
                ? "text-accent font-bold"
                : "text-text-muted hover:text-foreground"
            )}
          >
            {link.name}
            {activeSection === link.href.substring(1) && (
              <motion.div
                layoutId="activeNav"
                className="absolute bottom-0 left-0 right-0 h-[2px] bg-accent"
                transition={{ type: "spring", stiffness: 380, damping: 30 }}
              />
            )}
          </Link>
        ))}
      </div>

      {/* Auth Buttons */}
      <div className="hidden md:flex items-center gap-4">
        {user ? (
          <Button asChild className="bg-accent hover:bg-accent/90 text-foreground font-bold px-6 rounded-full transition-all hover:scale-105 active:scale-95">
            <Link href="/dashboard">
              DASHBOARD
            </Link>
          </Button>
        ) : (
          <>
            <Button asChild variant="ghost" className="text-text-muted hover:text-foreground font-bold">
              <Link href="/login">
                LOGIN
              </Link>
            </Button>
            <Button asChild className="bg-accent hover:bg-accent/90 text-foreground font-bold px-6 rounded-full transition-all hover:scale-105 active:scale-95">
              <Link href="/signup">
                GET STARTED
              </Link>
            </Button>
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
              className={cn(
                "text-lg font-medium transition-colors",
                activeSection === link.href.substring(1) ? "text-accent font-bold" : "text-text-muted"
              )}
              onClick={() => setMobileMenuOpen(false)}
            >
              {link.name}
            </Link>
          ))}
          <div className="flex flex-col gap-3 pt-4 border-t border-border">
            {user ? (
               <Button asChild className="w-full bg-accent text-foreground font-bold">
                 <Link href="/dashboard" onClick={() => setMobileMenuOpen(false)}>DASHBOARD</Link>
               </Button>
            ) : (
              <>
                <Button asChild variant="outline" className="w-full border-border text-foreground">
                  <Link href="/login" onClick={() => setMobileMenuOpen(false)}>LOGIN</Link>
                </Button>
                <Button asChild className="w-full bg-accent text-foreground font-bold">
                  <Link href="/signup" onClick={() => setMobileMenuOpen(false)}>GET STARTED</Link>
                </Button>
              </>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
