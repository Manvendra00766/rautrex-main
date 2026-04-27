import { useAuthStore } from '@/lib/auth-store'
import { createClient } from '@/lib/supabase'

jest.mock('@/lib/supabase')

describe('Auth Store', () => {
  let mockSignOut: jest.Mock
  
  beforeEach(() => {
    mockSignOut = jest.fn()
    ;(createClient as jest.Mock).mockReturnValue({
      auth: {
        signOut: mockSignOut,
        onAuthStateChange: jest.fn(),
      },
    })
    
    // Reset store before each test
    useAuthStore.setState({ user: null, isLoading: true })
  })

  test('test_user_set_on_valid_session: assert zustand store user updated', () => {
    const mockUser = { id: 'uuid-123', email: 'test@example.com' } as any
    useAuthStore.getState().setUser(mockUser)
    expect(useAuthStore.getState().user).toEqual(mockUser)
  })

  test('test_user_null_on_signout: assert store user=null', () => {
    useAuthStore.setState({ user: { id: 'uuid-123' } as any })
    useAuthStore.getState().setUser(null)
    expect(useAuthStore.getState().user).toBeNull()
  })
})
