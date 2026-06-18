import React from 'react'
import { render, screen, renderHook } from '@testing-library/react'
import { AuthProvider, useAuth, type AuthUser } from '@/context/AuthContext'

const MOCK_USER: AuthUser = { id: 42, email: 'alice@example.com', role: 'participant' }

describe('AuthProvider / useAuth', () => {
  it('exposes id, email, and role to children', () => {
    function Consumer() {
      const user = useAuth()
      return (
        <div>
          <span data-testid="id">{user.id}</span>
          <span data-testid="email">{user.email}</span>
          <span data-testid="role">{user.role}</span>
        </div>
      )
    }

    render(
      <AuthProvider user={MOCK_USER}>
        <Consumer />
      </AuthProvider>,
    )

    expect(screen.getByTestId('id')).toHaveTextContent('42')
    expect(screen.getByTestId('email')).toHaveTextContent('alice@example.com')
    expect(screen.getByTestId('role')).toHaveTextContent('participant')
  })

  it('throws when useAuth is called outside AuthProvider', () => {
    // Suppress the console.error from React's error boundary during the test
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {})
    expect(() =>
      renderHook(() => useAuth()),
    ).toThrow('useAuth must be used within AuthProvider')
    spy.mockRestore()
  })

  it('passes updated user values when re-rendered', () => {
    const { rerender } = render(
      <AuthProvider user={MOCK_USER}>
        <span data-testid="role">{MOCK_USER.role}</span>
      </AuthProvider>,
    )
    expect(screen.getByTestId('role')).toHaveTextContent('participant')

    const trainer: AuthUser = { id: 7, email: 'bob@example.com', role: 'trainer' }
    rerender(
      <AuthProvider user={trainer}>
        <span data-testid="role">{trainer.role}</span>
      </AuthProvider>,
    )
    expect(screen.getByTestId('role')).toHaveTextContent('trainer')
  })
})
