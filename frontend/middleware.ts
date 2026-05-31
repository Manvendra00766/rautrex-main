import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(req: NextRequest) {
  let res = NextResponse.next({
    request: {
      headers: req.headers,
    },
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return req.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            req.cookies.set(name, value)
          )
          res = NextResponse.next({
            request: {
              headers: req.headers,
            },
          })
          cookiesToSet.forEach(({ name, value, options }) =>
            res.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  // This will refresh session if expired - critical for SSR
  const { data: { session } } = await supabase.auth.getSession()

  const isAuthPage = req.nextUrl.pathname.startsWith('/login') || req.nextUrl.pathname.startsWith('/signup')
  const isProtectedPage = req.nextUrl.pathname.startsWith('/dashboard') || req.nextUrl.pathname.startsWith('/onboarding')

  // If no session and on protected page → go to login
  if (!session && isProtectedPage) {
    const redirectUrl = new URL('/login', req.url)
    redirectUrl.searchParams.set('expired', 'true')
    return NextResponse.redirect(redirectUrl)
  }
  
  // If has session and on auth page → go to dashboard
  if (session && isAuthPage) {
    return NextResponse.redirect(new URL('/dashboard', req.url))
  }
  
  // CRITICAL: return res with updated session cookies
  return res
}

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/onboarding',
    '/onboarding/:path*',
    '/login',
    '/signup',
  ]
}
