"use client";

import { useState } from "react";
import { Mail, Phone, MapPin, Send, HelpCircle } from "lucide-react";
import { motion } from "framer-motion";

export default function ContactPage() {
  const [formState, setFormState] = useState({
    name: "",
    email: "",
    subject: "support",
    message: ""
  });
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    setTimeout(() => {
      setSubmitted(false);
      setFormState({ name: "", email: "", subject: "support", message: "" });
    }, 3000);
  };

  return (
    <div className="bg-[var(--bg-primary)] min-h-screen text-[var(--text-primary)] font-sans">
      {/* Header Banner */}
      <section className="bg-[#2C2A1E] text-[#F5F0E8] py-28 px-6 text-center border-b border-border/20">
        <div className="max-w-4xl mx-auto space-y-6">
          <motion.p 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-accent text-xs font-black uppercase tracking-[0.3em]"
          >
            Get In Touch
          </motion.p>
          <motion.h1 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-4xl md:text-6xl font-extrabold tracking-tight text-[#F5F0E8]"
          >
            Connect With Our Desk
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-[#EDE8DC]/80 text-base md:text-lg max-w-xl mx-auto leading-relaxed"
          >
            Have technical questions about our mathematical models, API configurations, or institutional solutions? Reach out below.
          </motion.p>
        </div>
      </section>

      {/* Main Grid */}
      <section className="py-24 px-6 max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12">
        {/* Left Side: Info */}
        <div className="lg:col-span-5 space-y-8">
          <div className="space-y-4">
            <h2 className="text-accent text-xs font-black uppercase tracking-[0.3em]">Communication Desks</h2>
            <h2 className="text-3xl font-bold tracking-tight">Support & Partnership</h2>
            <p className="text-text-muted text-sm leading-relaxed">
              We operate dedicated communication desks for support, media requests, and institutional integrations. Expect replies from our engineering or support desk within 12 hours.
            </p>
          </div>

          <div className="space-y-6 pt-4">
            {[
              { icon: Mail, label: "Technical Support", val: "rautelamanvendra07@gmail.com" },
              { icon: Phone, label: "Institutional Hotline", val: "+91 807593467" },
              { icon: MapPin, label: "Quant Headquarters", val: "New Delhi, India" }
            ].map((item, idx) => (
              <div key={idx} className="flex gap-4 items-start p-4 rounded-xl bg-surface border border-border/60 shadow-sm">
                <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center text-accent shrink-0">
                  <item.icon size={20} />
                </div>
                <div>
                  <p className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-0.5">{item.label}</p>
                  <p className="font-mono text-sm font-black text-foreground">{item.val}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Side: Interactive Form */}
        <div className="lg:col-span-7">
          <div className="glass-panel p-8 md:p-10 rounded-[28px] bg-surface border border-border shadow-md">
            <h3 className="text-xl font-bold text-foreground mb-6 flex items-center gap-2">
              <Send size={18} className="text-accent" /> Dispatch Message
            </h3>

            {submitted ? (
              <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="p-8 text-center bg-positive/10 border border-positive/30 rounded-2xl space-y-4"
              >
                <div className="w-12 h-12 rounded-full bg-positive/20 text-positive flex items-center justify-center mx-auto text-xl font-bold">✓</div>
                <h4 className="text-positive font-bold">Transmission Successful</h4>
                <p className="text-text-muted text-xs leading-relaxed max-w-sm mx-auto">
                  Your message has been processed by our communication desk. A developer or support specialist will review your request shortly.
                </p>
              </motion.div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-text-secondary">Your Name</label>
                    <input 
                      suppressHydrationWarning
                      type="text" 
                      required
                      value={formState.name}
                      onChange={(e) => setFormState({ ...formState, name: e.target.value })}
                      placeholder="e.g. Alexis Carter"
                      className="w-full bg-[var(--bg-secondary)]/50 border border-border rounded-lg px-4 py-2.5 text-xs text-foreground placeholder-text-muted/50 focus:outline-none focus:border-accent/60 transition-colors"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-text-secondary">Email Address</label>
                    <input 
                      suppressHydrationWarning
                      type="email" 
                      required
                      value={formState.email}
                      onChange={(e) => setFormState({ ...formState, email: e.target.value })}
                      placeholder="alexis@domain.com"
                      className="w-full bg-[var(--bg-secondary)]/50 border border-border rounded-lg px-4 py-2.5 text-xs text-foreground placeholder-text-muted/50 focus:outline-none focus:border-accent/60 transition-colors"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-text-secondary">Topic Area</label>
                  <select 
                    suppressHydrationWarning
                    value={formState.subject}
                    onChange={(e) => setFormState({ ...formState, subject: e.target.value })}
                    className="w-full bg-[var(--bg-secondary)]/50 border border-border rounded-lg px-4 py-2.5 text-xs text-foreground focus:outline-none focus:border-accent/60 transition-colors"
                  >
                    <option value="support">Technical Core Support</option>
                    <option value="model">Quant Models / Mathematical Feedback</option>
                    <option value="api">API Access & Developers Integration</option>
                    <option value="business">Enterprise Partnerships</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-text-secondary">Detailed Inquiry</label>
                  <textarea 
                    suppressHydrationWarning
                    rows={5}
                    required
                    value={formState.message}
                    onChange={(e) => setFormState({ ...formState, message: e.target.value })}
                    placeholder="Enter your detailed query..."
                    className="w-full bg-[var(--bg-secondary)]/50 border border-border rounded-lg px-4 py-2.5 text-xs text-foreground placeholder-text-muted/50 focus:outline-none focus:border-accent/60 transition-colors resize-none"
                  />
                </div>

                <button 
                  suppressHydrationWarning
                  type="submit"
                  className="w-full bg-[#2C2A1E] hover:bg-[#2C2A1E]/95 text-[#F5F0E8] font-bold uppercase tracking-wider text-xs py-3 rounded-lg shadow-sm transition-all"
                >
                  Send Transmission
                </button>
              </form>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
