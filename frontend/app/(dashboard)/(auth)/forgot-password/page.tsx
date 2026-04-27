'use client'

import React, { useState } from 'react'
import { createClient } from '@/lib/supabase'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Loader2, ArrowLeft, MailCheck } from 'lucide-react'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  
  const supabase = createClient()

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)

    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    })

    if (error) {
      setError(error.message)
      setIsLoading(false)
    } else {
      setSuccess(true)
      setIsLoading(false)
    }
  }

  if (success) {
    return (
      <div className="flex items-center justify-center min-h-[80vh]">
        <div className="w-full max-w-md p-8 glass-panel rounded-2xl text-center space-y-4">
          <div className="mx-auto w-12 h-12 bg-accent/20 text-accent rounded-full flex items-center justify-center">
            <MailCheck size={24} />
          </div>
          <h1 className="text-2xl font-bold text-white">Reset link sent</h1>
          <p className="text-muted-foreground">
            We&apos;ve sent a password reset link to <span className="text-white font-medium">{email}</span>.
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
          <h1 className="text-3xl font-bold tracking-tight text-white">Reset Password</h1>
          <p className="text-muted-foreground">Enter your email to receive a reset link</p>
        </div>

        {error && (
          <div className="p-3 text-sm font-medium text-red-500 bg-red-500/10 border border-red-500/20 rounded-lg">
            {error}
          </div>
        )}

        <form onSubmit={handleReset} className="space-y-4">
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

          <Button type="submit" className="w-full bg-accent hover:bg-accent/90 text-black font-semibold" disabled={isLoading}>
            {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : 'Send Reset Link'}
          </Button>
        </form>

        <Link href="/login" className="flex items-center justify-center gap-2 text-sm text-muted-foreground hover:text-white transition-colors">
          <ArrowLeft size={14} />
          Back to Login
        </Link>
      </div>
    </div>
  )
}
