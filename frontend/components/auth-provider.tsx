'use client'

import React, { useEffect } from 'react'
import { createClient } from '@/lib/supabase'
import { useAuthStore } from '@/lib/auth-store'

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const { setUser, setIsLoading } = useAuthStore()
  const supabase = createClient()

  useEffect(() => {
    const initialize = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      setUser(session?.user ?? null)
      setIsLoading(false)

      const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
        setUser(session?.user ?? null)
        setIsLoading(false)
      })

      return () => subscription.unsubscribe()
    }

    initialize()
  }, [setUser, setIsLoading, supabase.auth])

  return <>{children}</>
}
