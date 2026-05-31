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

      const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
        setUser(session?.user ?? null)
        setIsLoading(false)

        // Log auth state changes for debugging
        switch (event) {
          case 'TOKEN_REFRESHED':

            break
          case 'SIGNED_OUT':

            break
          case 'SIGNED_IN':

            break
          case 'USER_UPDATED':

            break
        }
      })

      return () => subscription.unsubscribe()
    }

    initialize()
  }, [setUser, setIsLoading, supabase.auth])

  return <>{children}</>
}
