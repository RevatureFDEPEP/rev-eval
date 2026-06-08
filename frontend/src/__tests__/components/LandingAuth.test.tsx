import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { LandingAuth } from '@/app/_components/landing-auth'

const push = vi.fn()
const refresh = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push, refresh }),
}))

function okResponse() {
  return new Response('{}', { status: 200 })
}

describe('LandingAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // Restore the fetch spy after every test so a mocked fetch never leaks into a
  // later suite that touches the global.
  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('rendering', () => {
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

  describe('submission', () => {
    it('posts the login contract to /api/auth/login and navigates on success', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(okResponse())
      render(<LandingAuth />)

      fireEvent.change(screen.getByLabelText('Email'), {
        target: { value: 'user@example.com' },
      })
      fireEvent.change(screen.getByLabelText('Password'), {
        target: { value: 'secret123' },
      })
      fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

      await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1))
      expect(fetchSpy).toHaveBeenCalledWith('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'user@example.com', password: 'secret123' }),
      })
      await waitFor(() => expect(push).toHaveBeenCalledWith('/dashboard'))
      expect(refresh).toHaveBeenCalledTimes(1)
    })

    it('posts the registration contract with full_name and role to /api/auth/register', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(okResponse())
      render(<LandingAuth />)

      // Radix Tabs use automatic (focus-based) activation, so focusing the tab
      // switches mode; a bare click doesn't move focus in jsdom.
      fireEvent.focus(screen.getByRole('tab', { name: 'Register' }))
      const fullName = await screen.findByLabelText('Full name')
      fireEvent.change(fullName, { target: { value: 'Jane Doe' } })
      fireEvent.change(screen.getByLabelText('Email'), {
        target: { value: 'jane@example.com' },
      })
      fireEvent.change(screen.getByLabelText('Password'), {
        target: { value: 'secret123' },
      })
      fireEvent.click(screen.getByRole('button', { name: 'Register' }))

      await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1))
      expect(fetchSpy).toHaveBeenCalledWith('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'jane@example.com',
          password: 'secret123',
          full_name: 'Jane Doe',
          role: 'PARTICIPANT',
        }),
      })
      await waitFor(() => expect(push).toHaveBeenCalledWith('/dashboard'))
    })

    it('blocks submission and shows a Zod validation error when the password is too short', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(okResponse())
      render(<LandingAuth />)

      fireEvent.change(screen.getByLabelText('Email'), {
        target: { value: 'user@example.com' },
      })
      fireEvent.change(screen.getByLabelText('Password'), {
        target: { value: 'short' },
      })
      fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

      expect(
        await screen.findByText('Password must be at least 8 characters'),
      ).toBeInTheDocument()
      expect(fetchSpy).not.toHaveBeenCalled()
      expect(push).not.toHaveBeenCalled()
    })

    it('surfaces the server error and does not navigate when login fails', async () => {
      vi.spyOn(global, 'fetch').mockResolvedValue(
        new Response(JSON.stringify({ detail: 'Invalid credentials' }), {
          status: 401,
        }),
      )
      render(<LandingAuth />)

      fireEvent.change(screen.getByLabelText('Email'), {
        target: { value: 'user@example.com' },
      })
      fireEvent.change(screen.getByLabelText('Password'), {
        target: { value: 'wrongpass' },
      })
      fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

      expect(await screen.findByText('Invalid credentials')).toBeInTheDocument()
      expect(push).not.toHaveBeenCalled()
    })
  })
})
