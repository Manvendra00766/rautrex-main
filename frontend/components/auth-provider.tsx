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
            console.log('[Auth] Token refreshed successfully at', new Date().toISOString())
            break
          case 'SIGNED_OUT':
            console.log('[Auth] User signed out')
            break
          case 'SIGNED_IN':
            console.log('[Auth] User signed in')
            break
          case 'USER_UPDATED':
            console.log('[Auth] User profile updated')
            break
        }
      })

      return () => subscription.unsubscribe()
    }

    initialize()
  }, [setUser, setIsLoading, supabase.auth])

  return <>{children}</>
}
