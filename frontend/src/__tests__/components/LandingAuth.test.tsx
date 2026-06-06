import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LandingAuth } from '@/app/_components/landing-auth'

const push = vi.fn()
const refresh = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push, refresh }),
}))

describe('LandingAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn()
  })

  it('renders without crashing', () => {
    render(<LandingAuth />)
    expect(screen.getByText('Welcome')).toBeInTheDocument()
  })

  it('shows Sign in and Register tabs', () => {
    render(<LandingAuth />)
    expect(screen.getByRole('tab', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Register' })).toBeInTheDocument()
  })

  it('renders email and password inputs', () => {
    render(<LandingAuth />)
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
  })

  it('renders a submit button labelled Sign in by default', () => {
    render(<LandingAuth />)
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('does not show the full name field in login mode', () => {
    render(<LandingAuth />)
    expect(screen.queryByLabelText('Full name')).not.toBeInTheDocument()
  })
})
