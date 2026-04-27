import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import LoginPage from '@/app/(dashboard)/(auth)/login/page'
import { createClient } from '@/lib/supabase'
import { useRouter } from 'next/navigation'

// Mock the dependencies
jest.mock('@/lib/supabase')
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}))

describe('LoginPage', () => {
  let mockPush: jest.Mock
  let mockRefresh: jest.Mock
  let mockSignInWithPassword: jest.Mock
  let mockSignInWithOAuth: jest.Mock

  beforeEach(() => {
    mockPush = jest.fn()
    mockRefresh = jest.fn()
    ;(useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
      refresh: mockRefresh,
    })

    mockSignInWithPassword = jest.fn()
    mockSignInWithOAuth = jest.fn()
    ;(createClient as jest.Mock).mockReturnValue({
      auth: {
        signInWithPassword: mockSignInWithPassword,
        signInWithOAuth: mockSignInWithOAuth,
      },
    })
  })

  test('test_login_calls_signInWithPassword: Submit → assert supabase.auth.signInWithPassword({email, password}) called', async () => {
    mockSignInWithPassword.mockResolvedValue({ data: {}, error: null })
    
    render(<LoginPage />)
    
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'test@example.com' } })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'password123' } })
    
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
    
    await waitFor(() => {
      expect(mockSignInWithPassword).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      })
    })
  })

  test('test_login_success_redirects_dashboard: Mock valid session → assert router.push("/") called', async () => {
    mockSignInWithPassword.mockResolvedValue({ data: {}, error: null })
    
    render(<LoginPage />)
    
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'test@example.com' } })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'password123' } })
    
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
    
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/')
    })
  })

  test('test_login_error_shows_message: Mock error → assert error message rendered', async () => {
    mockSignInWithPassword.mockResolvedValue({ data: null, error: { message: 'Invalid credentials' } })
    
    render(<LoginPage />)
    
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'test@example.com' } })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'wrongpassword' } })
    
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
    })
  })

  test('test_google_button_calls_signInWithOAuth: Click Google button → assert supabase.auth.signInWithOAuth({provider:"google"}) called', async () => {
    render(<LoginPage />)
    
    fireEvent.click(screen.getByRole('button', { name: /google/i }))
    
    expect(mockSignInWithOAuth).toHaveBeenCalledWith(expect.objectContaining({
      provider: 'google',
    }))
  })

  test('test_show_hide_password_toggle: Click eye icon → input type changes from "password" to "text"', () => {
    render(<LoginPage />)
    
    const passwordInput = screen.getByLabelText(/password/i)
    expect(passwordInput).toHaveAttribute('type', 'password')
    
    const toggleButton = screen.getByRole('button', { name: '' }) // The eye icon button has no text
    fireEvent.click(toggleButton)
    
    expect(passwordInput).toHaveAttribute('type', 'text')
    
    fireEvent.click(toggleButton)
    expect(passwordInput).toHaveAttribute('type', 'password')
  })
})
