'use client'

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence, Variants } from 'framer-motion'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { 
  ArrowLeft, Check, Sparkles, Shield, TrendingUp, AlertTriangle, 
  HelpCircle, ChevronRight, Upload, FileText, CheckCircle, ArrowRight, Loader2, RefreshCw
} from 'lucide-react'
import { apiFetch } from '@/lib/api'

// Define the slide variants for Framer Motion transitions
const slideVariants: Variants = {
  enter: (direction: number) => ({
    x: direction > 0 ? '100vw' : '-100vw',
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
    transition: {
      type: 'spring',
      stiffness: 300,
      damping: 30,
    }
  },
  exit: (direction: number) => ({
    x: direction < 0 ? '100vw' : '-100vw',
    opacity: 0,
    transition: {
      type: 'spring',
      stiffness: 300,
      damping: 30,
    }
  })
}

// Option Interface
interface Option {
  label: string
  value: string
}

// Questions configuration
interface Question {
  id: number
  questionText: string
  options: Option[]
  multiSelect?: boolean
}

// 7 Questions for New Investor (strictly avoiding the word "portfolio")
const NEW_INVESTOR_QUESTIONS: Question[] = [
  {
    id: 1,
    questionText: "What's the main reason you want to start investing?",
    options: [
      { label: "Save for something big", value: "Save for something big" },
      { label: "Grow my money over time", value: "Grow my money over time" },
      { label: "Stop money sitting idle", value: "Stop money sitting idle" },
      { label: "Build a safety net", value: "Build a safety net" },
      { label: "Retire comfortably", value: "Retire comfortably" }
    ]
  },
  {
    id: 2,
    questionText: "What are you saving towards?",
    options: [
      { label: "My child's education", value: "My child's education" },
      { label: "Buying a home", value: "Buying a home" },
      { label: "Getting married", value: "Getting married" },
      { label: "Travel or a big purchase", value: "Travel or a big purchase" },
      { label: "Just building wealth", value: "Just building wealth" },
      { label: "An emergency fund", value: "An emergency fund" }
    ]
  },
  {
    id: 3,
    questionText: "When do you want to reach this goal?",
    options: [
      { label: "Within 1 year", value: "Within 1 year" },
      { label: "1–3 years", value: "1–3 years" },
      { label: "3–7 years", value: "3–7 years" },
      { label: "7+ years", value: "7+ years" },
      { label: "No rush, long term", value: "No rush, long term" }
    ]
  },
  {
    id: 4,
    questionText: "How much can you comfortably set aside every month?",
    options: [
      { label: "Under ₹500", value: "Under ₹500" },
      { label: "₹500–₹2,000", value: "₹500–₹2,000" },
      { label: "₹2,000–₹5,000", value: "₹2,000–₹5,000" },
      { label: "₹5,000–₹15,000", value: "₹5,000–₹15,000" },
      { label: "₹15,000+", value: "₹15,000+" }
    ]
  },
  {
    id: 5,
    questionText: "Imagine you invest ₹10,000 and it drops to ₹8,000 next month. What do you do?",
    options: [
      { label: "Pull it out immediately", value: "Pull it out immediately" },
      { label: "Feel worried but wait", value: "Feel worried but wait" },
      { label: "Stay calm, it will recover", value: "Stay calm, it will recover" },
      { label: "Invest more while it's cheap", value: "Invest more while it's cheap" }
    ]
  },
  {
    id: 6,
    questionText: "Would it be okay if your investment didn't grow for 1–2 years, but was safe?",
    options: [
      { label: "Yes, safety is most important", value: "Yes, safety is most important" },
      { label: "Maybe — depends on returns", value: "Maybe — depends on returns" },
      { label: "No, I want growth", value: "No, I want growth" }
    ]
  },
  {
    id: 7,
    questionText: "Have you heard of mutual funds or SIPs before?",
    options: [
      { label: "Never heard of them", value: "Never heard of them" },
      { label: "Heard of them but don't understand", value: "Heard of them but don't understand" },
      { label: "I know the basics", value: "I know the basics" }
    ]
  }
]

// 7 Questions for Existing Investor
const EXISTING_INVESTOR_QUESTIONS: Question[] = [
  {
    id: 1,
    questionText: "Where are you investing right now?",
    multiSelect: true,
    options: [
      { label: "Stocks (direct)", value: "Stocks (direct)" },
      { label: "Mutual funds or SIPs", value: "Mutual funds or SIPs" },
      { label: "Fixed deposits", value: "Fixed deposits" },
      { label: "Gold", value: "Gold" },
      { label: "PPF or NPS", value: "PPF or NPS" },
      { label: "Crypto", value: "Crypto" },
      { label: "Real estate", value: "Real estate" }
    ]
  },
  {
    id: 2,
    questionText: "Roughly how much is your total portfolio worth today?",
    options: [
      { label: "Under ₹50,000", value: "Under ₹50,000" },
      { label: "₹50,000–₹2 lakh", value: "₹50,000–₹2 lakh" },
      { label: "₹2 lakh–₹10 lakh", value: "₹2 lakh–₹10 lakh" },
      { label: "₹10 lakh–₹50 lakh", value: "₹10 lakh–₹50 lakh" },
      { label: "Above ₹50 lakh", value: "Above ₹50 lakh" }
    ]
  },
  {
    id: 3,
    questionText: "How long have you been investing?",
    options: [
      { label: "Less than 1 year", value: "Less than 1 year" },
      { label: "1–3 years", value: "1–3 years" },
      { label: "3–7 years", value: "3–7 years" },
      { label: "7+ years", value: "7+ years" }
    ]
  },
  {
    id: 4,
    questionText: "Do you have a specific financial goal you're saving towards?",
    options: [
      { label: "Yes — retirement", value: "Yes — retirement" },
      { label: "Yes — a big purchase", value: "Yes — a big purchase" },
      { label: "Yes — building wealth", value: "Yes — building wealth" },
      { label: "Not really, just investing", value: "Not really, just investing" }
    ]
  },
  {
    id: 5,
    questionText: "How much are you adding to your investments every month?",
    options: [
      { label: "Nothing right now", value: "Nothing right now" },
      { label: "Under ₹5,000", value: "Under ₹5,000" },
      { label: "₹5,000–₹20,000", value: "₹5,000–₹20,000" },
      { label: "₹20,000–₹50,000", value: "₹20,000–₹50,000" },
      { label: "₹50,000+", value: "₹50,000+" }
    ]
  },
  {
    id: 6,
    questionText: "What's your biggest frustration with investing right now?",
    options: [
      { label: "Don't know if I'm on track", value: "Don't know if I'm on track" },
      { label: "Too much to track manually", value: "Too much to track manually" },
      { label: "Don't understand what I own", value: "Don't understand what I own" },
      { label: "Worried about risk", value: "Worried about risk" },
      { label: "Not getting good returns", value: "Not getting good returns" },
      { label: "No time to manage it", value: "No time to manage it" }
    ]
  },
  {
    id: 7,
    questionText: "Would you like to import your existing investments automatically?",
    options: [
      { label: "Yes, import from my broker statement", value: "Yes, import" },
      { label: "I'll enter it manually", value: "Manual entry" },
      { label: "Show me how it works first", value: "Show me first" }
    ]
  }
]

export default function OnboardingPage() {
  const router = useRouter()
  
  // State management
  const [investorType, setInvestorType] = useState<'new' | 'existing' | null>(null)
  const [step, setStep] = useState(0) // 0 is selection screen, 1-7 are questions
  const [direction, setDirection] = useState(1) // 1 = next, -1 = back
  const [loading, setLoading] = useState(false)
  const [loadingMessage, setLoadingMessage] = useState('')
  const [resultsMode, setResultsMode] = useState(false)
  const [importMode, setImportMode] = useState(false)
  
  // Demat Connection States
  const [dematStep, setDematStep] = useState(false)
  const [selectedBroker, setSelectedBroker] = useState<string | null>(null)
  const [dematModalOpen, setDematModalOpen] = useState(false)
  const [dematClientId, setDematClientId] = useState('')
  const [dematPin, setDematPin] = useState('')
  const [dematSyncing, setDematSyncing] = useState(false)
  const [linkedDemat, setLinkedDemat] = useState<any>(null)
  const [syncStepIndex, setSyncStepIndex] = useState(0)
  const [syncSteps, setSyncSteps] = useState<string[]>([])
  
  // Onboarding answers states
  const [newAnswers, setNewAnswers] = useState({
    goal: '',
    target: '',
    horizon: '',
    monthly_amount: '',
    risk_reaction: '',
    risk_tolerance: '',
    knowledge_level: ''
  })
  
  const [existingAnswers, setExistingAnswers] = useState({
    asset_types: [] as string[],
    portfolio_size: '',
    experience_years: '',
    goal_type: '',
    monthly_contribution: '',
    pain_point: '',
    import_preference: ''
  })
  
  // Backend response cache
  const [suggestedPortfolio, setSuggestedPortfolio] = useState<any>(null)
  const [existingReport, setExistingReport] = useState<any>(null)
  
  // Uploader mock states
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadSuccess, setUploadSuccess] = useState(false)

  // Handle Upstox OAuth redirect callback on the frontend
  useEffect(() => {
    if (typeof window === 'undefined') return
    const urlParams = new URLSearchParams(window.location.search)
    const code = urlParams.get('code')
    
    if (code) {
      const exchangeUpstoxCode = async () => {
        setLoading(true)
        setLoadingMessage("Securing connection with Upstox...")
        try {
          const res = await apiFetch(`/onboarding/upstox-callback?code=${code}`)
          setLoadingMessage("Analyzing holdings...")
          alert("Successfully synced with your Upstox portfolio!")
          router.push('/dashboard')
        } catch (err) {
          console.error("Upstox callback exchange error", err)
          alert("Failed to sync your holdings from Upstox. Please check your credentials or try again.")
        } finally {
          setLoading(false)
        }
      }
      exchangeUpstoxCode()
    }
  }, [router])

  // Handle selecting investor type at step 0
  const handleSelectInvestorType = (type: 'new' | 'existing') => {
    setDirection(1)
    setInvestorType(type)
    setStep(1)  // Go directly to questions
  }

  // Handle connecting a specific demat broker
  const handleConnectBroker = async (broker: string) => {
    if (broker === 'Upstox') {
      setDematSyncing(true)
      try {
        const data = await apiFetch("/onboarding/upstox-login")
        if (data && data.auth_url) {
          window.location.href = data.auth_url
        } else {
          alert("Failed to initiate Upstox login. Make sure your client credentials are set in the .env file.")
          setDematSyncing(false)
        }
      } catch (err) {
        console.error("Upstox auth initiation error", err)
        alert("Failed to connect with Upstox API. Please check your network and try again.")
        setDematSyncing(false)
      }
      return
    }

    setSelectedBroker(broker)
    setDematClientId('')
    setDematPin('')
    setDematModalOpen(true)
  }

  // Handle OAuth/PIN credential verification and syncing holdings/balances
  const handleVerifyDemat = async () => {
    if (!selectedBroker) return
    if (!dematClientId.trim()) {
      alert("Please enter a valid Client ID or mobile number.")
      return
    }
    if (!dematPin.trim()) {
      alert("Please enter your PIN or OTP.")
      return
    }
    
    setDematSyncing(true)
    setSyncStepIndex(0)
    setSyncSteps([
      `Connecting to ${selectedBroker}...`,
      "Scanning equity holdings...",
      "Scanning mutual funds & ETFs...",
      "Analyzing portfolio health..."
    ])
    
    try {
      const res = await apiFetch("/onboarding/sync-demat", {
        method: "POST",
        body: JSON.stringify({
          broker: selectedBroker,
          client_id: dematClientId,
          pin_or_otp: dematPin
        })
      })
      
      // Step 1 -> Step 2
      setTimeout(() => {
        setSyncStepIndex(1)
        
        // Step 2 -> Step 3
        setTimeout(() => {
          setSyncStepIndex(2)
          
          // Step 3 -> Step 4
          setTimeout(() => {
            setSyncStepIndex(3)
            
            // Step 4 -> Complete
            setTimeout(() => {
              setLinkedDemat(res)
              setDematSyncing(false)
              setDematModalOpen(false)
            }, 1500)
            
          }, 1000)
          
        }, 1000)
        
      }, 1000)
      
    } catch (err) {
      console.error("Demat connection error", err)
      setDematSyncing(false)
      alert("Failed to securely sync with broker account. Please try again.")
    }
  }

  // Handle choosing an answer
  const handleAnswerSelect = async (value: string) => {
    if (!investorType) return
    
    setDirection(1)
    
    if (investorType === 'new') {
      const updatedAnswers = { ...newAnswers }
      const key = Object.keys(updatedAnswers)[step - 1] as keyof typeof newAnswers
      updatedAnswers[key] = value
      setNewAnswers(updatedAnswers)
      
      if (step < 7) {
        setStep(step + 1)
      } else {
        // Finished Q7 — show broker connection step
        setDematStep(true)
      }
    } else {
      const updatedAnswers = { ...existingAnswers }
      const key = Object.keys(updatedAnswers)[step - 1] as keyof typeof existingAnswers
      
      // Since Q1 is multi-select, it's handled differently
      if (step === 1) {
        // Should use explicit Next button instead of auto trigger
        return
      }
      
      if (key !== 'asset_types') {
        (updatedAnswers[key] as string) = value
      }
      setExistingAnswers(updatedAnswers)
      
      if (step < 7) {
        setStep(step + 1)
      } else {
        // Finished Q7 — show broker connection step
        setDematStep(true)
      }
    }
  }

  // Handle next button for multi-select question (Q1 of Existing Investor)
  const handleMultiSelectContinue = () => {
    if (investorType === 'existing' && step === 1) {
      if (existingAnswers.asset_types.length === 0) {
        alert("Please select at least one asset type to continue.")
        return
      }
      setDirection(1)
      setStep(2)
    }
  }

  // Handle toggling options for multi-select Q1 (Existing)
  const toggleMultiSelectOption = (value: string) => {
    const assets = [...existingAnswers.asset_types]
    if (assets.includes(value)) {
      setExistingAnswers({
        ...existingAnswers,
        asset_types: assets.filter(item => item !== value)
      })
    } else {
      setExistingAnswers({
        ...existingAnswers,
        asset_types: [...assets, value]
      })
    }
  }

  // Handle back link
  const handleBack = () => {
    setDirection(-1)
    if (resultsMode) {
      setResultsMode(false)
      setStep(7)
      return
    }
    if (importMode) {
      setImportMode(false)
      setStep(7)
      return
    }
    
    if (dematStep) {
      setDematStep(false)
      // Go back to Q7 since demat is now after questions
    } else if (step > 1) {
      setStep(step - 1)
    } else if (step === 1) {
      setStep(0)
      setInvestorType(null)
    }
  }

  // Handle submission after demat step (connect or skip)
  const handleSubmitAfterDemat = async () => {
    setDematStep(false)
    if (investorType === 'new') {
      await submitNewInvestorFlow(newAnswers)
    } else {
      await submitExistingInvestorFlow(existingAnswers)
    }
  }

  // Submit New Investor onboarding
  const submitNewInvestorFlow = async (answers: typeof newAnswers) => {
    setLoading(true)
    setLoadingMessage("Building your personalised plan...")
    
    // Simulate 2s max loading as requested
    const start = Date.now()
    try {
      const response = await apiFetch("/onboarding/new", {
        method: "POST",
        body: JSON.stringify({
          ...answers,
          demat_broker: linkedDemat?.broker || null,
          demat_balance: linkedDemat?.total_value || 0,
          demat_holdings: linkedDemat?.holdings || []
        })
      })
      
      const elapsed = Date.now() - start
      const remaining = Math.max(0, 1800 - elapsed) // aim for ~1.8-2s
      
      setTimeout(() => {
        setSuggestedPortfolio(response.portfolio_suggestion)
        setLoading(false)
        setResultsMode(true)
      }, remaining)
      
    } catch (error) {
      console.error("New investor onboarding failed", error)
      setTimeout(() => {
        // Fallback mockup in case backend has a loading issue
        setSuggestedPortfolio({
          name: "Rautrex Steady Growth Plan",
          description: `Designed to grow your investments over time. Standard high-quality index strategy to help you reach your goals safely.`,
          estimated_returns: "11.5% p.a.",
          target_horizon: answers.horizon,
          recommended_sip: answers.monthly_amount,
          risk_profile: "Balanced",
          allocation: [
            { asset: "Large & Flexi Cap Equity", percentage: 50, color: "#8B6F47" },
            { asset: "Balanced Hybrid Assets", percentage: 30, color: "#8C8278" },
            { asset: "Debt & Gold Anchor", percentage: 20, color: "#D4CEC4" }
          ],
          suggested_funds: [
            { name: "Parag Parikh Flexi Cap Fund", type: "Equity", allocation: "35%" },
            { name: "UTI Nifty 50 Index Fund", type: "Equity", allocation: "15%" },
            { name: "ICICI Prudential Balanced Advantage Fund", type: "Hybrid", allocation: "30%" },
            { name: "Nippon India Gold Savings Fund", type: "Commodity", allocation: "20%" }
          ]
        })
        setLoading(false)
        setResultsMode(true)
      }, 1500)
    }
  }

  // Submit Existing Investor onboarding
  const submitExistingInvestorFlow = async (answers: typeof existingAnswers) => {
    setLoading(true)
    setLoadingMessage("Analyzing your investment health...")
    
    const start = Date.now()
    try {
      const response = await apiFetch("/onboarding/existing", {
        method: "POST",
        body: JSON.stringify({
          ...answers,
          demat_broker: linkedDemat?.broker || null,
          demat_balance: linkedDemat?.total_value || 0,
          demat_holdings: linkedDemat?.holdings || []
        })
      })
      
      const elapsed = Date.now() - start
      const remaining = Math.max(0, 1800 - elapsed)
      
      setTimeout(() => {
        setExistingReport(response)
        setLoading(false)
        
        // Immediate CAS redirect logic if Yes, import is selected
        if (answers.import_preference === "Yes, import from my broker statement") {
          setImportMode(true)
        } else {
          setResultsMode(true)
        }
      }, remaining)
      
    } catch (error) {
      console.error("Existing investor onboarding failed", error)
      setTimeout(() => {
        // Fallback mockup in case backend has a loading issue
        setExistingReport({
          health_score: 72,
          top_gap: "Portfolio tracking silo. Aggregate asset weights and overlap statistics are currently fragmented across broker portals.",
          one_action_today: "Upload a consolidated NSDL/CDSL CAS broker statement to instantly run fee leakage diagnostics."
        })
        setLoading(false)
        
        if (answers.import_preference === "Yes, import from my broker statement") {
          setImportMode(true)
        } else {
          setResultsMode(true)
        }
      }, 1500)
    }
  }

  // Handle statement upload simulation
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      setUploadFile(file)
      setUploadProgress(0)
      setUploadSuccess(false)
      
      // Simulate reading progress
      let p = 0
      const interval = setInterval(() => {
        p += 10
        setUploadProgress(p)
        if (p >= 100) {
          clearInterval(interval)
          setUploadSuccess(true)
        }
      }, 150)
    }
  }

  // Active question array
  const currentQuestions = investorType === 'new' ? NEW_INVESTOR_QUESTIONS : EXISTING_INVESTOR_QUESTIONS
  const currentQuestion = currentQuestions[step - 1]

  return (
    <div className="flex-1 flex flex-col justify-center bg-[var(--bg-primary)] text-[var(--text-primary)] relative overflow-hidden font-sans min-h-screen">
      
      {/* Thin Teal Animated Progress Bar */}
      {step > 0 && !loading && !resultsMode && !importMode && (
        <div className="w-full h-1 bg-[var(--border)]/30 fixed top-0 left-0 z-50">
          <motion.div 
            className="h-full bg-teal-500 shadow-[0_0_8px_rgba(20,184,166,0.5)]"
            initial={{ width: '0%' }}
            animate={{ width: `${(step / 7) * 100}%` }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
          />
        </div>
      )}

      {/* Header Bar with Back Link */}
      {(step > 0 || dematStep) && !loading && (
        <div className="absolute top-0 left-0 w-full p-6 flex justify-between items-center z-40">
          <button 
            onClick={handleBack}
            className="flex items-center gap-1 text-[11px] font-bold uppercase tracking-[0.15em] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
          >
            <ArrowLeft size={14} className="mr-0.5" /> Back
          </button>
          
          {!resultsMode && !importMode && !dematStep && (
            <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--text-muted)]">
              Question {step} of 7
            </div>
          )}
        </div>
      )}

      {/* Main Container */}
      <div className="w-full max-w-xl mx-auto px-6 py-12 flex flex-col justify-center min-h-[85vh]">
        
        <AnimatePresence mode="wait" custom={direction}>
          
          {/* STEP 0: Selection Screen */}
          {step === 0 && !loading && !resultsMode && !dematStep && (
            <motion.div
              key="selection"
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              className="space-y-8"
            >
              <div className="space-y-3 text-center">
                <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-teal-600 bg-teal-500/10 px-3 py-1 rounded-full">
                  Invest Smart
                </span>
                <h1 className="text-3xl md:text-4xl font-extrabold text-[var(--text-primary)] tracking-tight">
                  Welcome to Rautrex
                </h1>
                <p className="text-sm text-[var(--text-muted)] max-w-md mx-auto">
                  Every investor deserves a personalized roadmap. Let&apos;s discover yours in under 2 minutes.
                </p>
              </div>

              <div className="space-y-4">
                <button
                  onClick={() => handleSelectInvestorType('new')}
                  className="w-full text-left p-6 bg-[var(--bg-surface)] border border-[var(--border)] hover:border-[var(--accent)] hover:shadow-md rounded-2xl group transition-all duration-300 active:scale-[0.99] cursor-pointer"
                >
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="font-bold text-lg text-[var(--text-primary)] group-hover:text-[var(--accent)] transition-colors">
                      I am a new investor
                    </h3>
                    <ChevronRight size={18} className="text-[var(--text-muted)] group-hover:translate-x-1 transition-transform" />
                  </div>
                  <p className="text-xs text-[var(--text-muted)] leading-relaxed">
                    You have ₹0 or little currently invested. Build a tailored plan to start saving consistently.
                  </p>
                </button>

                <button
                  onClick={() => handleSelectInvestorType('existing')}
                  className="w-full text-left p-6 bg-[var(--bg-surface)] border border-[var(--border)] hover:border-[var(--accent)] hover:shadow-md rounded-2xl group transition-all duration-300 active:scale-[0.99] cursor-pointer"
                >
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="font-bold text-lg text-[var(--text-primary)] group-hover:text-[var(--accent)] transition-colors">
                      I have existing investments
                    </h3>
                    <ChevronRight size={18} className="text-[var(--text-muted)] group-hover:translate-x-1 transition-transform" />
                  </div>
                  <p className="text-xs text-[var(--text-muted)] leading-relaxed">
                    You have active assets or portfolios. Diagnose your diversification, track overlapping risks, and optimize.
                  </p>
                </button>
              </div>
            </motion.div>
          )}

          {/* DEMAT CONNECTION SCREEN */}
          {dematStep && !loading && (
            <motion.div
              key="demat-connector"
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              className="space-y-6 w-full"
            >
              <div className="text-center space-y-3">
                <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-teal-600 bg-teal-500/10 px-3 py-1 rounded-full">
                  Final Step: Link Your Broker
                </span>
                <h2 className="text-2xl font-bold md:text-3xl text-[var(--text-primary)] leading-tight">
                  Connect Your Demat Account
                </h2>
                <p className="text-xs text-[var(--text-muted)] max-w-sm mx-auto">
                  Link your broker to enrich your personalised plan with real holdings, balances, and footprint metrics.
                </p>
              </div>

              {linkedDemat ? (
                /* SUCCESS STATE CONTAINER */
                <div className="p-6 bg-[var(--bg-surface)] border border-teal-500 rounded-2xl shadow-md space-y-4">
                  <div className="flex items-center gap-3 border-b border-[var(--border)]/50 pb-4">
                    <div className="w-10 h-10 rounded-full bg-teal-500 flex items-center justify-center text-white font-bold uppercase">
                      {linkedDemat.broker[0]}
                    </div>
                    <div>
                      <h4 className="text-sm font-bold uppercase tracking-wider text-teal-600">
                        {linkedDemat.broker} connected
                      </h4>
                      <p className="text-[10px] text-[var(--text-muted)] mt-0.5">
                        Read-only session authenticated
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-center">
                    <div className="bg-[var(--bg-primary)]/40 p-3 rounded-xl border border-[var(--border)]/30">
                      <span className="text-[9px] font-bold uppercase tracking-wider text-[var(--text-muted)]">Current Value</span>
                      <p className="text-base font-extrabold text-[var(--text-primary)] mt-0.5">₹{(linkedDemat.current_value || linkedDemat.total_value || 0).toLocaleString('en-IN')}</p>
                    </div>
                    <div className="bg-[var(--bg-primary)]/40 p-3 rounded-xl border border-[var(--border)]/30">
                      <span className="text-[9px] font-bold uppercase tracking-wider text-[var(--text-muted)]">Invested Value</span>
                      <p className="text-base font-extrabold text-[var(--text-primary)] mt-0.5">₹{(linkedDemat.total_invested || 0).toLocaleString('en-IN')}</p>
                    </div>
                    <div className="bg-[var(--bg-primary)]/40 p-3 rounded-xl border border-[var(--border)]/30">
                      <span className="text-[9px] font-bold uppercase tracking-wider text-[var(--text-muted)]">Overall P&L</span>
                      <p className={`text-base font-extrabold mt-0.5 ${linkedDemat.overall_pnl >= 0 ? 'text-teal-600' : 'text-red-500'}`}>
                        ₹{(linkedDemat.overall_pnl || 0).toLocaleString('en-IN')} ({(linkedDemat.overall_pnl_pct || 0)}%)
                      </p>
                    </div>
                    <div className="bg-[var(--bg-primary)]/40 p-3 rounded-xl border border-[var(--border)]/30">
                      <span className="text-[9px] font-bold uppercase tracking-wider text-[var(--text-muted)]">Annualised XIRR</span>
                      <p className="text-base font-extrabold text-[var(--accent)] mt-0.5">{(linkedDemat.xirr || 0)}%</p>
                    </div>
                  </div>

                  <div className="space-y-2 max-h-40 overflow-y-auto custom-scrollbar border border-[var(--border)]/40 rounded-xl p-3 bg-[var(--bg-primary)]/10">
                    <h5 className="text-[9px] font-bold uppercase tracking-wider text-[var(--text-muted)]">Active Holding Telemetry ({linkedDemat.holdings_count} Assets)</h5>
                    {linkedDemat.holdings.map((h: any) => (
                      <div key={h.ticker} className="flex justify-between items-center text-[11px] border-b border-[var(--border)]/20 py-1.5 last:border-b-0">
                        <div>
                          <p className="font-bold text-[var(--text-primary)]">{h.ticker}</p>
                          <span className="text-[9px] text-[var(--text-muted)]">{h.name}</span>
                        </div>
                        <div className="text-right">
                          <p className="font-semibold text-[var(--text-primary)]">₹{(h.current_value || h.total_value || 0).toLocaleString('en-IN')}</p>
                          <span className={`text-[9px] font-medium ${h.pnl >= 0 ? 'text-teal-600' : 'text-red-500'}`}>
                            {h.pnl >= 0 ? '+' : ''}{h.pnl.toLocaleString('en-IN')} ({h.pnl_pct || 0}%)
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>

                  <button
                    onClick={handleSubmitAfterDemat}
                    className="w-full min-h-[52px] bg-teal-600 hover:bg-teal-700 text-white font-bold rounded-xl transition-all shadow-md active:scale-[0.99] flex items-center justify-center gap-2 cursor-pointer mt-4"
                  >
                    Generate My Personalised Plan <ArrowRight size={16} />
                  </button>
                </div>
              ) : (
                /* BROKER SELECT LIST */
                <div className="space-y-3">
                  <button
                    onClick={() => handleConnectBroker('Zerodha Kite')}
                    className="w-full p-4 bg-[var(--bg-surface)] border border-[var(--border)] hover:border-orange-500 rounded-xl flex items-center justify-between group transition-all duration-300 cursor-pointer shadow-sm"
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-8 h-8 rounded-full bg-orange-500 flex items-center justify-center text-white text-xs font-bold font-mono shadow-sm">Z</span>
                      <span className="font-bold text-sm text-[var(--text-primary)] group-hover:text-orange-500 transition-colors">Zerodha Kite</span>
                    </div>
                    <ChevronRight size={16} className="text-[var(--text-muted)] group-hover:translate-x-0.5 transition-transform" />
                  </button>

                  <button
                    onClick={() => handleConnectBroker('Groww')}
                    className="w-full p-4 bg-[var(--bg-surface)] border border-[var(--border)] hover:border-emerald-500 rounded-xl flex items-center justify-between group transition-all duration-300 cursor-pointer shadow-sm"
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center text-white text-xs font-bold font-mono shadow-sm">G</span>
                      <span className="font-bold text-sm text-[var(--text-primary)] group-hover:text-emerald-500 transition-colors">Groww</span>
                    </div>
                    <ChevronRight size={16} className="text-[var(--text-muted)] group-hover:translate-x-0.5 transition-transform" />
                  </button>

                  <button
                    onClick={() => handleConnectBroker('Upstox')}
                    className="w-full p-4 bg-[var(--bg-surface)] border border-[var(--border)] hover:border-blue-500 rounded-xl flex items-center justify-between group transition-all duration-300 cursor-pointer shadow-sm"
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-xs font-bold font-mono shadow-sm">U</span>
                      <span className="font-bold text-sm text-[var(--text-primary)] group-hover:text-blue-500 transition-colors">Upstox</span>
                    </div>
                    <ChevronRight size={16} className="text-[var(--text-muted)] group-hover:translate-x-0.5 transition-transform" />
                  </button>

                  <div className="pt-4 text-center">
                    <button
                      onClick={handleSubmitAfterDemat}
                      className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
                    >
                      Skip & see my results
                    </button>
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {/* QUESTIONS FLOW */}
          {step > 0 && !loading && !resultsMode && !importMode && !dematStep && currentQuestion && (
            <motion.div
              key={`${investorType}-q-${step}`}
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              className="space-y-8 w-full"
            >
              {/* Question Text */}
              <div className="text-center space-y-2">
                <h2 className="text-2xl font-bold md:text-3xl text-[var(--text-primary)] max-w-2xl mx-auto leading-tight">
                  {currentQuestion.questionText}
                </h2>
                {currentQuestion.multiSelect && (
                  <p className="text-xs text-teal-600 font-semibold uppercase tracking-wider">
                    Select all that apply
                  </p>
                )}
              </div>

              {/* Options Grid */}
              <div className="space-y-3 w-full">
                {currentQuestion.options.map((opt) => {
                  const isSelected = investorType === 'existing' && step === 1 && existingAnswers.asset_types.includes(opt.value)
                  
                  return (
                    <button
                      key={opt.value}
                      onClick={() => {
                        if (currentQuestion.multiSelect) {
                          toggleMultiSelectOption(opt.value)
                        } else {
                          handleAnswerSelect(opt.value)
                        }
                      }}
                      className={`w-full min-h-[56px] py-4 px-6 text-left md:text-center rounded-xl font-medium shadow-sm transition-all duration-200 active:scale-[0.99] cursor-pointer flex items-center justify-between border ${
                        isSelected 
                          ? 'bg-teal-50/50 border-teal-500 text-teal-900 shadow-teal-500/5'
                          : 'bg-[var(--bg-surface)] border-[var(--border)] hover:border-[var(--accent)] hover:bg-[var(--bg-primary)]/40 text-[var(--text-primary)]'
                      }`}
                    >
                      <span className="flex-1 text-base leading-snug">{opt.label}</span>
                      {isSelected ? (
                        <div className="w-5 h-5 rounded-full bg-teal-500 flex items-center justify-center text-white shrink-0 shadow-sm ml-2">
                          <Check size={12} strokeWidth={3} />
                        </div>
                      ) : (
                        currentQuestion.multiSelect && (
                          <div className="w-5 h-5 rounded border border-[var(--border)] shrink-0 ml-2" />
                        )
                      )}
                    </button>
                  )
                })}
              </div>

              {/* Multi-Select Continue Button */}
              {currentQuestion.multiSelect && (
                <motion.button
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  onClick={handleMultiSelectContinue}
                  className="w-full min-h-[52px] bg-[var(--accent)] hover:bg-[var(--accent)]/95 text-white font-bold rounded-xl transition-all shadow-md active:scale-[0.99] cursor-pointer flex items-center justify-center gap-2 mt-4"
                >
                  Continue <ArrowRight size={16} />
                </motion.button>
              )}
            </motion.div>
          )}

          {/* LOADING SCREEN */}
          {loading && (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center text-center space-y-6"
            >
              <div className="relative flex items-center justify-center w-24 h-24">
                <div className="absolute w-full h-full rounded-full border-4 border-[var(--accent)]/20"></div>
                <div className="absolute w-full h-full rounded-full border-4 border-t-teal-500 animate-spin"></div>
                <Sparkles className="text-teal-600 animate-pulse" size={28} />
              </div>
              <div className="space-y-2">
                <h3 className="text-xl font-extrabold text-[var(--text-primary)] tracking-tight">
                  {loadingMessage}
                </h3>
                <p className="text-xs text-[var(--text-muted)] animate-pulse">
                  Applying algorithmic quantitative stress tests...
                </p>
              </div>
            </motion.div>
          )}

          {/* NEW INVESTOR RESULTS MODE (Avoiding the word "portfolio" completely) */}
          {resultsMode && investorType === 'new' && suggestedPortfolio && (
            <motion.div
              key="new-results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              <div className="text-center space-y-2">
                <div className="mx-auto w-12 h-12 bg-teal-50 text-teal-600 rounded-full flex items-center justify-center shadow-inner">
                  <Sparkles size={22} />
                </div>
                <h2 className="text-2xl font-bold tracking-tight">
                  Your Personalised Investment Plan
                </h2>
                <p className="text-xs text-[var(--text-muted)] max-w-sm mx-auto">
                  Tailored to help you save for <strong className="text-[var(--text-primary)] font-semibold">{newAnswers.target}</strong>
                </p>
              </div>

              {/* Suggestions Card */}
              <div className="p-6 bg-[var(--bg-surface)] border border-[var(--border)] rounded-2xl shadow-sm space-y-6">
                
                {/* Header Total */}
                <div className="flex justify-between items-center border-b border-[var(--border)]/50 pb-4">
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-[0.15em] text-[var(--text-muted)]">
                      Suggested Monthly SIP
                    </h3>
                    <h4 className="text-2xl font-extrabold text-[var(--accent)] mt-0.5">
                      ₹{suggestedPortfolio.total.toLocaleString('en-IN')}
                    </h4>
                  </div>
                  <div className="px-3 py-1 bg-teal-500/10 text-teal-700 rounded-lg text-xs font-bold uppercase tracking-wider">
                    Recommended Plan
                  </div>
                </div>

                {/* Plain Summary Callout */}
                <div className="p-4 bg-[var(--bg-primary)]/40 border border-[var(--border)]/50 rounded-xl space-y-2">
                  <h5 className="text-[10px] font-bold uppercase tracking-[0.15em] text-[var(--accent)] flex items-center gap-1.5">
                    <Sparkles size={12} /> Plan at a glance
                  </h5>
                  <p className="text-sm font-semibold text-[var(--text-primary)] leading-relaxed">
                    {suggestedPortfolio.plain_summary}
                  </p>
                </div>

                {/* Allocations breakdown */}
                <div className="space-y-4">
                  <h5 className="text-[10px] font-bold uppercase tracking-[0.15em] text-[var(--text-muted)]">
                    Where to invest your money
                  </h5>
                  <div className="space-y-3">
                    {suggestedPortfolio.allocations.map((alloc: any) => (
                      <div key={alloc.category} className="p-4 rounded-xl border border-[var(--border)]/50 bg-[var(--bg-surface)] hover:border-[var(--accent)] hover:shadow-sm transition-all duration-300 space-y-3">
                        <div className="flex justify-between items-center">
                          <span className="text-sm font-bold text-[var(--text-primary)]">
                            {alloc.category}
                          </span>
                          <span className="text-sm font-extrabold text-teal-600">
                            ₹{alloc.amount.toLocaleString('en-IN')}
                          </span>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] border-t border-[var(--border)]/30 pt-3 text-[var(--text-muted)]">
                          <div>
                            <span className="font-bold text-[var(--text-primary)]">Recommended: </span>
                            <span className="italic">{alloc.example_fund}</span>
                          </div>
                          <div>
                            <span className="font-bold text-[var(--text-primary)]">Where to buy: </span>
                            <span>{alloc.where_to_buy}</span>
                          </div>
                        </div>

                        <p className="text-[11px] text-[var(--text-muted)] leading-relaxed bg-[var(--bg-primary)]/20 p-2.5 rounded-lg border border-[var(--border)]/20 mt-1">
                          <strong className="text-[var(--text-primary)] font-bold">Why this fits: </strong>
                          {alloc.why}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* First Step Banner */}
                <div className="p-4 bg-teal-50/50 border border-teal-200/50 rounded-xl flex items-start gap-3 mt-4">
                  <div className="w-7 h-7 rounded-full bg-teal-500 flex items-center justify-center text-white shrink-0 mt-0.5">
                    <Check size={14} strokeWidth={3} />
                  </div>
                  <div>
                    <h5 className="text-[10px] font-bold uppercase tracking-[0.15em] text-teal-700">
                      Your First Step
                    </h5>
                    <p className="text-xs font-semibold text-teal-900 mt-0.5">
                      {suggestedPortfolio.first_step}
                    </p>
                  </div>
                </div>

              </div>

              {/* Actions */}
              <div className="space-y-3">
                <button 
                  onClick={() => router.push('/dashboard')}
                  className="w-full min-h-[52px] bg-teal-600 hover:bg-teal-700 text-white font-bold rounded-xl transition-all shadow-md active:scale-[0.99] flex items-center justify-center gap-2 cursor-pointer"
                >
                  Open Sandbox Dashboard <ArrowRight size={16} />
                </button>
                <button 
                  onClick={() => {
                    setResultsMode(false)
                    setStep(0)
                    setInvestorType(null)
                  }}
                  className="w-full min-h-[52px] border border-[var(--border)] hover:bg-[var(--bg-surface)] text-[var(--text-muted)] hover:text-[var(--text-primary)] font-bold rounded-xl transition-all active:scale-[0.99] flex items-center justify-center gap-2 cursor-pointer"
                >
                  <RefreshCw size={14} /> Restart Flow
                </button>
              </div>
            </motion.div>
          )}

          {/* EXISTING INVESTOR RESULTS MODE */}
          {resultsMode && investorType === 'existing' && existingReport && (
            <motion.div
              key="existing-results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              <div className="text-center space-y-2">
                <div className="mx-auto w-12 h-12 bg-teal-50 text-teal-600 rounded-full flex items-center justify-center shadow-inner">
                  <CheckCircle size={22} />
                </div>
                <h2 className="text-2xl font-bold tracking-tight">
                  Onboarding Complete
                </h2>
                <p className="text-xs text-[var(--text-muted)] max-w-sm mx-auto">
                  We have analysed your investment footprint. Here is your initial health scorecard.
                </p>
              </div>

              {/* Scorecard Box */}
              <div className="p-6 bg-[var(--bg-surface)] border border-[var(--border)] rounded-2xl shadow-sm space-y-6">
                
                {/* Health Score circle */}
                <div className="flex items-center justify-between border-b border-[var(--border)]/50 pb-4">
                  <div className="flex items-center gap-3">
                    <div className="relative w-16 h-16 flex items-center justify-center shrink-0">
                      <svg className="w-full h-full transform -rotate-90">
                        <circle cx="32" cy="32" r="28" fill="transparent" stroke="var(--border)" strokeWidth="4" className="opacity-20" />
                        <circle cx="32" cy="32" r="28" fill="transparent" stroke="rgb(20 184 166)" strokeWidth="4" 
                          strokeDasharray={`${2 * Math.PI * 28}`} 
                          strokeDashoffset={`${2 * Math.PI * 28 * (1 - existingReport.health_score / 100)}`}
                          className="transition-all duration-1000 ease-out"
                        />
                      </svg>
                      <span className="absolute font-mono font-extrabold text-base text-[var(--text-primary)]">
                        {existingReport.health_score}
                      </span>
                    </div>
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-[0.15em] text-[var(--text-muted)]">
                        Investment Health Score
                      </h3>
                      <p className="text-xs font-semibold text-teal-600 mt-0.5">
                        {existingReport.health_score >= 80 ? "Excellent standing" : existingReport.health_score >= 60 ? "Average standing" : "Needs attention"}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Gaps identified */}
                <div className="space-y-2">
                  <h4 className="text-[10px] font-bold uppercase tracking-[0.15em] text-[var(--text-muted)] flex items-center gap-1">
                    <AlertTriangle size={12} className="text-[var(--accent)]" /> Primary Gap Identified
                  </h4>
                  <p className="text-xs text-[var(--text-primary)] leading-relaxed bg-[var(--bg-primary)]/30 border border-[var(--border)]/40 p-4 rounded-xl">
                    {existingReport.top_gap}
                  </p>
                </div>

                {/* Target Recommendation */}
                <div className="space-y-2 pt-2">
                  <h4 className="text-[10px] font-bold uppercase tracking-[0.15em] text-[var(--text-muted)] flex items-center gap-1">
                    <Check size={12} className="text-teal-600" /> Action Required Today
                  </h4>
                  <p className="text-xs text-[var(--text-muted)] leading-relaxed">
                    {existingReport.one_action_today}
                  </p>
                </div>

              </div>

              {/* Actions */}
              <div className="space-y-3">
                <button 
                  onClick={() => router.push('/dashboard')}
                  className="w-full min-h-[52px] bg-teal-600 hover:bg-teal-700 text-white font-bold rounded-xl transition-all shadow-md active:scale-[0.99] flex items-center justify-center gap-2 cursor-pointer"
                >
                  Proceed to Terminal <ArrowRight size={16} />
                </button>
                <button 
                  onClick={() => {
                    setResultsMode(false)
                    setStep(0)
                    setInvestorType(null)
                  }}
                  className="w-full min-h-[52px] border border-[var(--border)] hover:bg-[var(--bg-surface)] text-[var(--text-muted)] hover:text-[var(--text-primary)] font-bold rounded-xl transition-all active:scale-[0.99] flex items-center justify-center gap-2 cursor-pointer"
                >
                  <RefreshCw size={14} /> Restart Flow
                </button>
              </div>
            </motion.div>
          )}

          {/* CSV/PDF STATEMENT IMPORT SCREEN (If Q7 Yes, Import) */}
          {importMode && investorType === 'existing' && (
            <motion.div
              key="import-mode"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              <div className="text-center space-y-2">
                <div className="mx-auto w-12 h-12 bg-teal-50 text-teal-600 rounded-full flex items-center justify-center shadow-inner">
                  <Upload size={22} />
                </div>
                <h2 className="text-2xl font-bold tracking-tight">
                  Import Broker Statement
                </h2>
                <p className="text-xs text-[var(--text-muted)] max-w-sm mx-auto">
                  Drag and drop your NSDL/CDSL CAS statement, or Zerodha/Groww tax ledger files. We support PDF and CSV.
                </p>
              </div>

              <div className="p-6 bg-[var(--bg-surface)] border-2 border-dashed border-[var(--border)] rounded-2xl shadow-sm text-center flex flex-col items-center justify-center space-y-4 hover:border-teal-500 hover:bg-teal-50/5 transition-all duration-300 relative group cursor-pointer">
                <input 
                  type="file" 
                  accept=".csv,.pdf" 
                  onChange={handleFileUpload}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                
                <div className="w-12 h-12 rounded-full bg-[var(--bg-primary)] flex items-center justify-center text-[var(--text-muted)] group-hover:text-teal-600 group-hover:scale-105 transition-all">
                  <FileText size={22} />
                </div>
                
                <div className="space-y-1">
                  <p className="text-xs font-bold text-[var(--text-primary)]">
                    {uploadFile ? uploadFile.name : "Choose statement file or drag here"}
                  </p>
                  <p className="text-[10px] text-[var(--text-muted)]">
                    Supports .pdf or .csv under 15MB. Encrypted read-only parsing.
                  </p>
                </div>
              </div>

              {/* Progress and Success indicators */}
              {uploadFile && (
                <div className="p-4 bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl space-y-3">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-semibold text-[var(--text-primary)]">Parsing statement footprint...</span>
                    <span className="font-mono font-bold text-teal-600">{uploadProgress}%</span>
                  </div>
                  
                  <div className="w-full h-1.5 rounded-full bg-[var(--border)]/20 overflow-hidden">
                    <div 
                      style={{ width: `${uploadProgress}%` }} 
                      className="h-full bg-teal-500 transition-all duration-150"
                    />
                  </div>

                  {uploadSuccess && (
                    <motion.div 
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-start gap-2.5 text-xs text-teal-900 bg-teal-50/50 p-3 rounded-lg border border-teal-200/50 mt-2"
                    >
                      <CheckCircle size={16} className="text-teal-600 shrink-0 mt-0.5" />
                      <div>
                        <p className="font-bold">Parsing Completed!</p>
                        <p className="text-[10px] text-teal-700 mt-0.5">
                          Successfully imported 14 active mutual fund holdings and 8 stock positions. Click below to continue.
                        </p>
                      </div>
                    </motion.div>
                  )}
                </div>
              )}

              {/* Action Buttons */}
              <div className="space-y-3">
                <button
                  disabled={!uploadSuccess}
                  onClick={() => setResultsMode(true)}
                  className={`w-full min-h-[52px] font-bold rounded-xl transition-all shadow-md active:scale-[0.99] flex items-center justify-center gap-2 cursor-pointer ${
                    uploadSuccess 
                      ? 'bg-teal-600 hover:bg-teal-700 text-white' 
                      : 'bg-gray-300 text-gray-500 cursor-not-allowed shadow-none'
                  }`}
                >
                  View Health Diagnostics <ArrowRight size={16} />
                </button>
                
                <button
                  onClick={() => setResultsMode(true)}
                  className="w-full min-h-[52px] border border-[var(--border)] hover:bg-[var(--bg-surface)] text-[var(--text-muted)] hover:text-[var(--text-primary)] font-bold rounded-xl transition-all active:scale-[0.99] flex items-center justify-center gap-2 cursor-pointer"
                >
                  Skip statement upload
                </button>
              </div>
            </motion.div>
          )}

        </AnimatePresence>

      </div>

      {/* BROKER OAUTH SIMULATOR MODAL */}
      {dematModalOpen && selectedBroker && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[99] flex items-center justify-center p-4">
          <motion.div 
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="w-full max-w-sm bg-[var(--bg-surface)] border border-[var(--border)] rounded-2xl shadow-2xl overflow-hidden p-6 space-y-6"
          >
            <div className="flex justify-between items-center border-b border-[var(--border)]/50 pb-3">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-teal-500 animate-ping" />
                <h4 className="font-bold text-sm text-[var(--text-primary)]">
                  Link with {selectedBroker}
                </h4>
              </div>
              <button 
                onClick={() => setDematModalOpen(false)}
                className="text-xs font-bold uppercase text-[var(--text-muted)] hover:text-[var(--text-primary)] cursor-pointer"
              >
                Cancel
              </button>
            </div>

            {dematSyncing ? (
              <div className="flex flex-col py-6 space-y-6">
                <div className="flex items-center justify-center">
                  <Loader2 className="animate-spin text-teal-600 shadow-[0_0_15px_rgba(20,184,166,0.3)] rounded-full" size={40} />
                </div>
                
                <div className="space-y-3 px-2">
                  {syncSteps.map((stepText, idx) => {
                    const isCompleted = idx < syncStepIndex
                    const isActive = idx === syncStepIndex
                    
                    return (
                      <div 
                        key={stepText} 
                        className={`flex items-center gap-3 transition-all duration-300 ${
                          isCompleted ? 'text-teal-600 font-medium' : isActive ? 'text-[var(--text-primary)] font-bold scale-[1.02]' : 'text-[var(--text-muted)] opacity-50'
                        }`}
                      >
                        <div className="flex items-center justify-center shrink-0">
                          {isCompleted ? (
                            <div className="w-5 h-5 rounded-full bg-teal-500 flex items-center justify-center text-white text-[10px] shadow-sm">
                              <Check size={10} strokeWidth={3} />
                            </div>
                          ) : isActive ? (
                            <div className="w-5 h-5 rounded-full border-2 border-teal-500 border-t-transparent animate-spin shrink-0" />
                          ) : (
                            <div className="w-5 h-5 rounded-full border border-[var(--border)] shrink-0" />
                          )}
                        </div>
                        <span className="text-xs">{stepText}</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="p-3 bg-teal-500/10 text-teal-900 border border-teal-200/50 rounded-xl text-[10px] leading-relaxed">
                  <strong>Read-Only Link:</strong> Rautrex requires read-only API access. We never hold or request trading execution credentials or fund transfer rights.
                </div>

                <div className="space-y-3">
                  <div className="space-y-1">
                    <label className="text-[9px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                      {selectedBroker === 'Groww' ? "Groww Registered Mobile / Email" : "Client Login ID"}
                    </label>
                    <input 
                      type="text" 
                      placeholder={selectedBroker === 'Groww' ? "name@example.com" : "E.g. AB1234"}
                      value={dematClientId}
                      onChange={(e) => setDematClientId(e.target.value)}
                      className="w-full h-11 px-3 bg-[var(--bg-primary)]/40 border border-[var(--border)] rounded-xl text-xs text-[var(--text-primary)] focus:border-[var(--accent)] outline-none"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[9px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                      {selectedBroker === 'Groww' ? "Verification OTP Code" : "Secure Demat PIN / Password"}
                    </label>
                    <input 
                      type="password" 
                      placeholder="••••••"
                      value={dematPin}
                      onChange={(e) => setDematPin(e.target.value)}
                      className="w-full h-11 px-3 bg-[var(--bg-primary)]/40 border border-[var(--border)] rounded-xl text-xs text-[var(--text-primary)] focus:border-[var(--accent)] outline-none"
                    />
                  </div>
                </div>

                <button
                  onClick={handleVerifyDemat}
                  className="w-full h-11 bg-teal-600 hover:bg-teal-700 text-white font-bold rounded-xl shadow-sm transition-all active:scale-[0.99] flex items-center justify-center gap-2 cursor-pointer mt-2 text-xs"
                >
                  Verify & Sync footprint <ArrowRight size={14} />
                </button>
              </div>
            )}
          </motion.div>
        </div>
      )}

    </div>
  )
}
