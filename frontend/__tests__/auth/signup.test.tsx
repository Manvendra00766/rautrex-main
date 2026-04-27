import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import SignupPage from '@/app/(dashboard)/(auth)/signup/page'
import { createClient } from '@/lib/supabase'
import { useRouter } from 'next/navigation'

// Mock the dependencies
jest.mock('@/lib/supabase')
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}))

describe('SignupPage', () => {
  let mockPush: jest.Mock
  let mockSignUp: jest.Mock

  beforeEach(() => {
    mockPush = jest.fn()
    ;(useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
    })

    mockSignUp = jest.fn()
    ;(createClient as jest.Mock).mockReturnValue({
      auth: {
        signUp: mockSignUp,
      },
    })
  })

  test('test_signup_calls_supabase: Submit → assert supabase.auth.signUp({email, password}) called', async () => {
    mockSignUp.mockResolvedValue({ data: {}, error: null })
    
    render(<SignupPage />)
    
    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'John Doe' } })
    fireEvent.change(screen.getByLabelText(/^email/i), { target: { value: 'test@example.com' } })
    fireEvent.change(screen.getByLabelText(/^password/i), { target: { value: 'StrongPass123!' } })
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'StrongPass123!' } })
    fireEvent.click(screen.getByRole('checkbox'))
    
    fireEvent.submit(screen.getByRole('form'))
    
    await waitFor(() => {
      expect(mockSignUp).toHaveBeenCalled()
    })
  })

  test('test_password_confirm_match: mismatch → assert error message', async () => {
    render(<SignupPage />)
    
    fireEvent.change(screen.getByLabelText(/^password/i), { target: { value: 'StrongPass123!' } })
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'Mismatch123!' } })
    fireEvent.click(screen.getByRole('checkbox'))
    
    fireEvent.submit(screen.getByRole('form'))
    
    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument()
    })
    expect(mockSignUp).not.toHaveBeenCalled()
  })

  test('test_terms_checkbox_required: Unchecked terms → assert signUp NOT called', async () => {
    render(<SignupPage />)
    
    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'John Doe' } })
    fireEvent.change(screen.getByLabelText(/^email/i), { target: { value: 'test@example.com' } })
    fireEvent.change(screen.getByLabelText(/^password/i), { target: { value: 'StrongPass123!' } })
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'StrongPass123!' } })
    
    fireEvent.submit(screen.getByRole('form'))
    
    await waitFor(() => {
      expect(screen.getByText(/you must accept the terms/i)).toBeInTheDocument()
    })
    expect(mockSignUp).not.toHaveBeenCalled()
  })

  test('test_signup_progress_bar: as password typed → assert indicators change', () => {
    render(<SignupPage />)
    
    const passwordInput = screen.getByLabelText(/^password/i)
    
    fireEvent.change(passwordInput, { target: { value: 'weak' } })
    expect(screen.getByText(/8\+ characters/i).parentElement).toHaveClass('text-muted-foreground')
    
    fireEvent.change(passwordInput, { target: { value: 'StrongPass123!' } })
    expect(screen.getByText(/8\+ characters/i).parentElement).toHaveClass('text-green-500')
    expect(screen.getByText(/uppercase letter/i).parentElement).toHaveClass('text-green-500')
    expect(screen.getByText(/contains number/i).parentElement).toHaveClass('text-green-500')
    expect(screen.getByText(/special character/i).parentElement).toHaveClass('text-green-500')
  })
})
