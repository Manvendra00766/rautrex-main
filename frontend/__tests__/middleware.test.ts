import { middleware } from '@/middleware'
import { NextRequest, NextResponse } from 'next/server'
import { createServerClient } from '@supabase/ssr'

jest.mock('@supabase/ssr')
jest.mock('next/server', () => ({
  NextResponse: {
    next: jest.fn().mockReturnValue({ cookies: { set: jest.fn() } }),
    redirect: jest.fn().mockImplementation((url) => ({ url })),
  },
}))

describe('Middleware', () => {
  let mockGetSession: jest.Mock

  beforeEach(() => {
    mockGetSession = jest.fn()
    ;(createServerClient as jest.Mock).mockReturnValue({
      auth: {
        getSession: mockGetSession,
      },
    })
  })

  test('test_middleware_redirects_unauthenticated: Mock getSession=null → / request → redirect to /login', async () => {
    mockGetSession.mockResolvedValue({ data: { session: null } })
    
    const request = {
      nextUrl: { pathname: '/' },
      url: 'http://localhost:3000/',
      cookies: { get: jest.fn() },
      headers: new Headers(),
    } as any

    const result = await middleware(request)
    
    expect(NextResponse.redirect).toHaveBeenCalledWith(expect.objectContaining({
      href: 'http://localhost:3000/login'
    }))
  })

  test('test_middleware_allows_authenticated: Mock valid session → / → passes through', async () => {
    mockGetSession.mockResolvedValue({ data: { session: { user: {} } } })
    
    const request = {
      nextUrl: { pathname: '/' },
      url: 'http://localhost:3000/',
      cookies: { get: jest.fn() },
      headers: new Headers(),
    } as any

    await middleware(request)
    
    expect(NextResponse.next).toHaveBeenCalled()
  })

  test('test_middleware_allows_public_routes: /login → no redirect even without session', async () => {
    mockGetSession.mockResolvedValue({ data: { session: null } })
    
    const request = {
      nextUrl: { pathname: '/login' },
      url: 'http://localhost:3000/login',
      cookies: { get: jest.fn() },
      headers: new Headers(),
    } as any

    await middleware(request)
    
    expect(NextResponse.next).toHaveBeenCalled()
  })
})
