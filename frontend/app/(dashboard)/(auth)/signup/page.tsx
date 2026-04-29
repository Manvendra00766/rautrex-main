'use client'

import React, { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Eye, EyeOff, Loader2, Check, X } from 'lucide-react'
import { Progress } from '@/components/ui/progress'

export default function SignupPage() {
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  
  const [strength, setStrength] = useState(0)
  const [checks, setChecks] = useState({
    length: false,
    number: false,
    upper: false,
    special: false,
  })

  useEffect(() => {
    const newChecks = {
      length: password.length >= 8,
      number: /[0-9]/.test(password),
      upper: /[A-Z]/.test(password),
      special: /[^A-Za-z0-9]/.test(password),
    }
    setChecks(newChecks)
    
    const count = Object.values(newChecks).filter(Boolean).length
    setStrength((count / 4) * 100)
  }, [password])

  const router = useRouter()
  const supabase = createClient()

  const [acceptTerms, setAcceptTerms] = useState(false)

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!acceptTerms) {
      setError('You must accept the terms and conditions')
      return
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    if (strength < 100) {
      setError('Please meet all password requirements')
      return
    }

    setIsLoading(true)
    setError(null)

    const trimmedEmail = email.trim()
    const trimmedPassword = password.trim()

    // Use environment variable for production, fallback to window.location.origin for local dev
    const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || window.location.origin
    const redirectTo = `${siteUrl}/auth/callback`

    const { data, error } = await supabase.auth.signUp({
      email: trimmedEmail,
      password: trimmedPassword,
      options: {
        data: {
          full_name: fullName,
        },
        emailRedirectTo: redirectTo,
      },
    })

    if (error) {
      setError(error.message)
      setIsLoading(false)
    } else {
      // If user exists but is unconfirmed, Supabase might not return an error 
      // but identities will be empty if "Allow Unconfirmed Logins" is off.
      if (data.user && data.user.identities?.length === 0) {
        setError("This email is already registered. Try logging in or resetting your password.")
        setIsLoading(false)
      } else {
        setSuccess(true)
        setIsLoading(false)
      }
    }
  }

  if (success) {
    return (
      <div className="flex items-center justify-center min-h-[80vh]">
        <div className="w-full max-w-md p-8 glass-panel rounded-2xl text-center space-y-4">
          <div className="mx-auto w-12 h-12 bg-green-500/20 text-green-500 rounded-full flex items-center justify-center">
            <Check size={24} />
          </div>
          <h1 className="text-2xl font-bold text-white">Check your email</h1>
          <p className="text-muted-foreground">
            We&apos;ve sent a verification link to <span className="text-white font-medium">{email}</span>. 
            Please check your inbox to activate your account.
          </p>
          <Button asChild className="w-full mt-4 bg-accent hover:bg-accent/90 text-black font-semibold">
            <Link href="/login">Return to Login</Link>
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center min-h-[80vh]">
      <div className="w-full max-w-md p-8 glass-panel rounded-2xl space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-3xl font-bold tracking-tight text-white">Create Account</h1>
          <p className="text-muted-foreground">Join the next generation of quant trading</p>
        </div>

        {error && (
          <div className="p-3 text-sm font-medium text-red-500 bg-red-500/10 border border-red-500/20 rounded-lg">
            {error}
          </div>
        )}

        <form onSubmit={handleSignup} className="space-y-4" role="form">
          <div className="space-y-2">
            <Label htmlFor="fullName">Full Name</Label>
            <Input
              id="fullName"
              placeholder="John Doe"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
              className="bg-white/5 border-white/10"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="bg-white/5 border-white/10"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="bg-white/5 border-white/10 pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-white"
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            
            {password.length > 0 && (
              <div className="space-y-2 mt-2">
                <Progress value={strength} className="h-1 bg-white/5" />
                <div className="grid grid-cols-2 gap-2 text-[10px]">
                  <Requirement met={checks.length} text="8+ characters" />
                  <Requirement met={checks.upper} text="Uppercase letter" />
                  <Requirement met={checks.number} text="Contains number" />
                  <Requirement met={checks.special} text="Special character" />
                </div>
              </div>
            )}
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="confirmPassword">Confirm Password</Label>
            <Input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className="bg-white/5 border-white/10"
            />
          </div>

          <div className="flex items-start space-x-2 py-2">
            <input
              id="terms"
              type="checkbox"
              checked={acceptTerms}
              onChange={(e) => setAcceptTerms(e.target.checked)}
              className="mt-1 h-4 w-4 rounded border-white/10 bg-white/5 text-accent focus:ring-accent"
            />
            <Label htmlFor="terms" className="text-xs leading-none text-muted-foreground peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
              I agree to the{' '}
              <Link href="/terms" className="text-accent hover:underline">
                Terms of Service
              </Link>{' '}
              and{' '}
              <Link href="/privacy" className="text-accent hover:underline">
                Privacy Policy
              </Link>
            </Label>
          </div>

          <Button type="submit" className="w-full bg-accent hover:bg-accent/90 text-black font-semibold" disabled={isLoading}>
            {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : 'Create Account'}
          </Button>
        </form>

        <p className="text-center text-sm text-muted-foreground">
          Already have an account?{' '}
          <Link href="/login" className="text-accent hover:underline">
            Login
          </Link>
        </p>
      </div>
    </div>
  )
}

function Requirement({ met, text }: { met: boolean; text: string }) {
  return (
    <div className={`flex items-center gap-1.5 ${met ? 'text-green-500' : 'text-muted-foreground'}`}>
      {met ? <Check size={10} /> : <X size={10} />}
      <span>{text}</span>
    </div>
  )
}
