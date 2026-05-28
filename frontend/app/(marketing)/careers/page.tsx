"use client";

import { useState } from "react";
import { Terminal, Code2, Database, Briefcase, FileText, Send, ArrowRight } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function CareersPage() {
  const [selectedJob, setSelectedJob] = useState<number | null>(null);
  const [applied, setApplied] = useState(false);
  const [resumeName, setResumeName] = useState("");

  const jobOpenings = [
    {
      id: 1,
      title: "Quantitative Developer (Rust / C++)",
      team: "Core Infrastructure",
      location: "New Delhi, India (Hybrid)",
      type: "Full-Time",
      icon: Terminal,
      description: "Build, optimize, and maintain our high-throughput market data feed pipelines and portfolio simulation engine. Work directly on lower latency scenarios computation.",
      requirements: [
        "3+ years of professional development experience in Rust, C++, or modern Go",
        "Deep understanding of low-latency networking, memory-mapped I/O, and concurrency",
        "Degree in Computer Science, Applied Mathematics, Physics, or equivalent quantitative field",
        "Prior experience with direct market feeds (e.g., FIX, ITCH, OUCH) is a strong plus"
      ]
    },
    {
      id: 2,
      title: "Senior Frontend Engineer (Next.js / TypeScript)",
      team: "UI/UX & Visuals",
      location: "Remote / New Delhi, India",
      type: "Full-Time",
      icon: Code2,
      description: "Own the flagship RAUTREX trading terminal frontend. Design and implement fast, responsive, and stunning reactive data visualizations using Next.js and lightweight WebGL-based charts.",
      requirements: [
        "5+ years of production experience in high-end React/Next.js and TypeScript ecosystems",
        "Strong knowledge of charting libraries (e.g., Lightweight Charts, D3.js, WebGL) and motion libraries",
        "Obsessive attention to micro-interactions, responsive CSS layouts, and performance optimization",
        "Understanding of finance, options math, or statistical charting is highly desirable"
      ]
    },
    {
      id: 3,
      title: "Quantitative Data Engineer (Python / PySpark)",
      team: "Data Pipelines & ML",
      location: "New York, NY (Hybrid)",
      type: "Full-Time",
      icon: Database,
      description: "Maintain historical datasets and construct modern distributed data pipelines for backtesting and machine learning models (LSTM, XGBoost directional forecasts).",
      requirements: [
        "3+ years of experience constructing data lakes and distributed storage layers (S3, Parquet, PySpark)",
        "Proficiency in Python quantitative libraries: NumPy, Pandas, Scikit-learn, PyTorch",
        "Familiarity with financial data, tickers mapping, corporate actions adjustment, and survivorship bias"
      ]
    }
  ];

  const handleApply = (e: React.FormEvent) => {
    e.preventDefault();
    setApplied(true);
    setTimeout(() => {
      setApplied(false);
      setSelectedJob(null);
      setResumeName("");
    }, 3000);
  };

  return (
    <div className="bg-[var(--bg-primary)] min-h-screen text-[var(--text-primary)] font-sans">
      {/* Hero Header */}
      <section className="bg-[#2C2A1E] text-[#F5F0E8] py-28 px-6 text-center border-b border-border/20">
        <div className="max-w-4xl mx-auto space-y-6">
          <motion.p 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-accent text-xs font-black uppercase tracking-[0.3em]"
          >
            Work With Us
          </motion.p>
          <motion.h1 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-4xl md:text-6xl font-extrabold tracking-tight text-[#F5F0E8]"
          >
            Engineering the Future of Retail Quant
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-[#EDE8DC]/80 text-base md:text-lg max-w-xl mx-auto leading-relaxed"
          >
            We are looking for builders, developers, and designers who thrive at the intersection of mathematical precision and high-quality frontend design.
          </motion.p>
        </div>
      </section>

      {/* Main Roles Section */}
      <section className="py-24 px-6 max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12">
        <div className="lg:col-span-6 space-y-6">
          <div className="space-y-4 mb-8">
            <h2 className="text-accent text-xs font-black uppercase tracking-[0.3em]">Open Positions</h2>
            <h2 className="text-3xl font-bold tracking-tight">Active Opportunities</h2>
            <p className="text-text-muted text-sm leading-relaxed">
              If you have a strong background in mathematics, computer science, or financial engineering, click on any listing to apply immediately.
            </p>
          </div>

          <div className="space-y-4">
            {jobOpenings.map((job) => (
              <div 
                key={job.id}
                onClick={() => {
                  setSelectedJob(job.id);
                  setApplied(false);
                }}
                className={`p-6 rounded-2xl border transition-all cursor-pointer shadow-sm ${
                  selectedJob === job.id 
                    ? "border-accent bg-surface ring-1 ring-accent/30" 
                    : "border-border/60 bg-surface hover:border-accent/40"
                }`}
              >
                <div className="flex gap-4">
                  <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center text-accent shrink-0">
                    <job.icon size={20} />
                  </div>
                  <div className="space-y-2 flex-1">
                    <div className="flex justify-between items-start gap-4">
                      <h3 className="text-base font-bold text-foreground leading-snug">{job.title}</h3>
                      <span className="text-[9px] font-bold uppercase tracking-wider text-accent bg-accent/10 px-2 py-0.5 rounded">
                        {job.type}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-muted font-medium">
                      <span>{job.team}</span>
                      <span>•</span>
                      <span>{job.location}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Dynamic Apply Drawer/Card */}
        <div className="lg:col-span-6">
          <AnimatePresence mode="wait">
            {selectedJob !== null ? (
              <motion.div 
                key={selectedJob}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                className="glass-panel p-8 md:p-10 rounded-[28px] bg-surface border border-border shadow-md space-y-6"
              >
                {(() => {
                  const job = jobOpenings.find(j => j.id === selectedJob)!;
                  return (
                    <>
                      <div className="space-y-2 pb-4 border-b border-border/40">
                        <div className="flex justify-between items-center">
                          <p className="text-accent text-[10px] font-mono font-bold uppercase tracking-widest">{job.team}</p>
                          <button 
                            onClick={() => setSelectedJob(null)}
                            className="text-xs text-text-muted hover:text-foreground font-bold"
                          >
                            Close
                          </button>
                        </div>
                        <h3 className="text-2xl font-bold tracking-tight text-foreground">{job.title}</h3>
                        <p className="text-xs text-text-muted font-medium">{job.location} • {job.type}</p>
                      </div>

                      {applied ? (
                        <motion.div 
                          initial={{ opacity: 0, scale: 0.95 }}
                          animate={{ opacity: 1, scale: 1 }}
                          className="p-8 text-center bg-positive/10 border border-positive/30 rounded-2xl space-y-4"
                        >
                          <div className="w-12 h-12 rounded-full bg-positive/20 text-positive flex items-center justify-center mx-auto text-xl font-bold">✓</div>
                          <h4 className="text-positive font-bold">Application Dispatched</h4>
                          <p className="text-text-muted text-xs leading-relaxed max-w-sm mx-auto">
                            Thank you for applying for the {job.title} role. Our recruiting and quant desk team will evaluate your telemetry data and contact you.
                          </p>
                        </motion.div>
                      ) : (
                        <div className="space-y-6">
                          <div className="space-y-3">
                            <h4 className="text-xs font-bold text-foreground uppercase tracking-wider">Role Overview</h4>
                            <p className="text-text-secondary text-xs leading-relaxed font-medium">{job.description}</p>
                          </div>

                          <div className="space-y-3">
                            <h4 className="text-xs font-bold text-foreground uppercase tracking-wider">Requirements</h4>
                            <ul className="list-disc pl-5 text-text-secondary text-xs leading-relaxed space-y-2">
                              {job.requirements.map((req, index) => (
                                <li key={index}>{req}</li>
                              ))}
                            </ul>
                          </div>

                          <form onSubmit={handleApply} className="pt-4 border-t border-border/40 space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                              <div className="space-y-1">
                                <label className="text-[9px] font-bold uppercase tracking-wider text-text-muted">Full Name</label>
                                <input 
                                  suppressHydrationWarning
                                  type="text" required placeholder="John Doe"
                                  className="w-full bg-[var(--bg-secondary)]/50 border border-border rounded px-3 py-2 text-xs focus:outline-none focus:border-accent"
                                />
                              </div>
                              <div className="space-y-1">
                                <label className="text-[9px] font-bold uppercase tracking-wider text-text-muted">Email Address</label>
                                <input 
                                  suppressHydrationWarning
                                  type="email" required placeholder="john@domain.com"
                                  className="w-full bg-[var(--bg-secondary)]/50 border border-border rounded px-3 py-2 text-xs focus:outline-none focus:border-accent"
                                />
                              </div>
                            </div>

                            <div className="space-y-2">
                              <label className="text-[9px] font-bold uppercase tracking-wider text-text-muted">Resume Submission (PDF/DOCX)</label>
                              <div className="border border-dashed border-border rounded-lg p-6 text-center hover:border-accent/40 cursor-pointer relative bg-[var(--bg-secondary)]/10">
                                <input 
                                  type="file" required accept=".pdf,.docx"
                                  onChange={(e) => {
                                    if (e.target.files?.[0]) setResumeName(e.target.files[0].name);
                                  }}
                                  className="absolute inset-0 opacity-0 cursor-pointer" 
                                />
                                <Briefcase size={24} className="mx-auto text-accent mb-2 opacity-60" />
                                <p className="text-[10px] text-text-secondary font-bold uppercase">
                                  {resumeName ? `Uploaded: ${resumeName}` : "Choose file or drag here"}
                                </p>
                              </div>
                            </div>

                            <button 
                              suppressHydrationWarning
                              type="submit"
                              className="w-full bg-[#2C2A1E] hover:bg-[#2C2A1E]/95 text-[#F5F0E8] font-bold uppercase tracking-wider text-xs py-3 rounded-lg shadow-sm transition-all flex items-center justify-center gap-2"
                            >
                              Submit Candidacy <Send size={12} />
                            </button>
                          </form>
                        </div>
                      )}
                    </>
                  );
                })()}
              </motion.div>
            ) : (
              <div className="border border-dashed border-border/80 rounded-[28px] p-12 text-center flex flex-col items-center justify-center min-h-[400px] bg-[var(--bg-secondary)]/10">
                <Briefcase size={36} className="text-accent opacity-50 mb-4" />
                <h3 className="text-lg font-bold text-foreground mb-2">No Position Selected</h3>
                <p className="text-xs text-text-muted max-w-xs leading-relaxed">
                  Select an active role from the list on the left to read full requirements, responsibilities, and send your candidacy directly to our engineering desk.
                </p>
              </div>
            )}
          </AnimatePresence>
        </div>
      </section>
    </div>
  );
}
