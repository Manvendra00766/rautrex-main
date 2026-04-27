import Link from "next/link";

export default function Footer() {
  return (
    <footer className="bg-background border-t border-white/5 pt-20 pb-10 px-6">
      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-12 mb-20">
        <div className="space-y-6">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-6 h-6 bg-accent rounded-sm cyan-glow" />
            <span className="font-mono font-black text-xl tracking-tighter text-white">RAUTREX</span>
          </Link>
          <p className="text-gray-500 text-sm leading-relaxed">
            Institutional-grade quant finance terminal for the next generation of retail traders.
          </p>
          <div className="flex gap-4">
            {/* Social icons placeholder */}
            {[1,2,3,4].map(i => (
              <div key={i} className="w-8 h-8 rounded-full bg-surface border border-white/5 flex items-center justify-center hover:border-accent/50 cursor-pointer transition-colors" />
            ))}
          </div>
        </div>

        <div>
          <h4 className="text-white font-bold text-sm uppercase tracking-widest mb-6">Product</h4>
          <ul className="space-y-4 text-sm text-gray-500">
            <li><Link href="/signals" className="hover:text-accent transition-colors">ML Signals</Link></li>
            <li><Link href="/backtest" className="hover:text-accent transition-colors">Backtester</Link></li>
            <li><Link href="/monte-carlo" className="hover:text-accent transition-colors">Monte Carlo</Link></li>
            <li><Link href="/options" className="hover:text-accent transition-colors">Options Pricing</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="text-white font-bold text-sm uppercase tracking-widest mb-6">Company</h4>
          <ul className="space-y-4 text-sm text-gray-500">
            <li><Link href="#about" className="hover:text-accent transition-colors">About Us</Link></li>
            <li><Link href="/contact" className="hover:text-accent transition-colors">Contact</Link></li>
            <li><Link href="/careers" className="hover:text-accent transition-colors">Careers</Link></li>
            <li><Link href="/blog" className="hover:text-accent transition-colors">Quant Blog</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="text-white font-bold text-sm uppercase tracking-widest mb-6">Legal</h4>
          <ul className="space-y-4 text-sm text-gray-500">
            <li><Link href="/privacy" className="hover:text-accent transition-colors">Privacy Policy</Link></li>
            <li><Link href="/terms" className="hover:text-accent transition-colors">Terms of Service</Link></li>
            <li><Link href="/disclaimer" className="hover:text-accent transition-colors">Risk Disclaimer</Link></li>
          </ul>
        </div>
      </div>

      <div className="max-w-7xl mx-auto pt-8 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-4">
        <p className="text-gray-600 text-[10px] uppercase font-bold tracking-widest">
          &copy; {new Date().getFullYear()} RAUTREX TECHNOLOGIES. ALL RIGHTS RESERVED.
        </p>
        <p className="text-gray-700 text-[10px]">
          Investments in securities market are subject to market risks. Read all the related documents carefully before investing.
        </p>
      </div>
    </footer>
  );
}
