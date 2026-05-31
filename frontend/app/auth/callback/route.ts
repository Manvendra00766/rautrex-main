import { createServerSupabaseClient } from '@/lib/supabase-server'
import { NextResponse } from 'next/server'

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')
  // if "next" is in search params, use it as the redirection URL
  const next = searchParams.get('next') ?? '/dashboard'

  if (code) {
    const supabase = await createServerSupabaseClient()
    const { error } = await supabase.auth.exchangeCodeForSession(code)
    
    if (!error) {
      // Use the SITE_URL if defined, otherwise the origin of the request
      const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || origin
      
      let redirectUrl = `${siteUrl}${next}`
      
      // If logging into the main dashboard, check if they have completed onboarding
      if (next === '/dashboard') {
        try {
          const { data: portfolios, error: portError } = await supabase
            .from('portfolios')
            .select('id')
            .limit(1)
            
          // If no portfolios exist, this is a first-time Google signup — redirect to onboarding!
          if (!portError && (!portfolios || portfolios.length === 0)) {
            redirectUrl = `${siteUrl}/onboarding`
          }
        } catch (e) {
          console.error('[Auth Callback] Failed checking user portfolios:', e)
        }
      }
      
      return NextResponse.redirect(redirectUrl)
    }
  }

  // return the user to an error page with instructions
  return NextResponse.redirect(`${origin}/login?error=verification_failed`)
}
