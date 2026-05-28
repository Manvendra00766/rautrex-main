import Link from "next/link";

export default function Footer() {
  return (
    <footer className="bg-background border-t border-border pt-20 pb-10 px-6">
      <div className="max-w-7xl mx-auto grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-12 mb-20">
        <div className="space-y-6 md:col-span-1">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-6 h-6 bg-accent rounded-sm" />
            <span className="font-mono font-black text-xl tracking-tighter text-foreground">RAUTREX</span>
          </Link>
          <p className="text-foreground text-sm leading-relaxed">
            Institutional-grade quant finance terminal for the next generation of retail traders.
          </p>
          <div className="flex gap-4">
            {/* Social icons placeholder */}
            {[1,2,3,4].map(i => (
              <div key={i} className="w-8 h-8 rounded-full bg-elevated border border-border flex items-center justify-center hover:border-accent/50 cursor-pointer transition-colors" />
            ))}
          </div>
        </div>

        <div>
          <h4 className="text-foreground font-bold text-sm uppercase tracking-widest mb-6">Product</h4>
          <ul className="space-y-4 text-sm text-foreground">
            <li><Link href="/dashboard/signals" className="hover:text-accent transition-colors">ML Signals</Link></li>
            <li><Link href="/dashboard/backtest" className="hover:text-accent transition-colors">Backtester</Link></li>
            <li><Link href="/dashboard/monte-carlo" className="hover:text-accent transition-colors">Monte Carlo</Link></li>
            <li><Link href="/dashboard/options" className="hover:text-accent transition-colors">Options Pricing</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="text-foreground font-bold text-sm uppercase tracking-widest mb-6">Resources</h4>
          <ul className="space-y-4 text-sm text-foreground">
            <li><Link href="/docs" className="hover:text-accent transition-colors">Documentation</Link></li>
            <li><Link href="/api" className="hover:text-accent transition-colors">API Docs</Link></li>
            <li><Link href="/community" className="hover:text-accent transition-colors">Community</Link></li>
            <li><Link href="/#roadmap" className="hover:text-accent transition-colors">Roadmap</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="text-foreground font-bold text-sm uppercase tracking-widest mb-6">Company</h4>
          <ul className="space-y-4 text-sm text-foreground">
            <li><Link href="/about" className="hover:text-accent transition-colors">About Us</Link></li>
            <li><Link href="/contact" className="hover:text-accent transition-colors">Contact</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="text-foreground font-bold text-sm uppercase tracking-widest mb-6">Legal</h4>
          <ul className="space-y-4 text-sm text-foreground">
            <li><Link href="/privacy" className="hover:text-accent transition-colors">Privacy Policy</Link></li>
            <li><Link href="/terms" className="hover:text-accent transition-colors">Terms of Service</Link></li>
            <li><Link href="/disclaimer" className="hover:text-accent transition-colors">Risk Disclaimer</Link></li>
          </ul>
        </div>
      </div>

      <div className="max-w-7xl mx-auto pt-8 pb-4 border-t border-border flex flex-wrap gap-x-8 gap-y-4 justify-center md:justify-start items-center text-[11px] font-bold tracking-wider text-accent uppercase">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-accent" />
          Bank-Grade Security
        </div>
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-accent" />
          Read-Only Broker Integration
        </div>
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-accent" />
          Data Encrypted (AES-256)
        </div>
      </div>

      <div className="max-w-7xl mx-auto pt-6 border-t border-border flex flex-col md:flex-row justify-between items-center gap-4">
        <p className="text-foreground text-[10px] uppercase font-bold tracking-widest">
          &copy; {new Date().getFullYear()} RAUTREX TECHNOLOGIES. ALL RIGHTS RESERVED.
        </p>
        <p className="text-text-muted text-[10px] text-center md:text-right max-w-lg">
          Investments in securities market are subject to market risks. Read all the related documents carefully before investing.
        </p>
      </div>
    </footer>
  );
}
