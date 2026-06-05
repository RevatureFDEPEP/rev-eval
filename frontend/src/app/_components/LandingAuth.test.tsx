import { describe, expect, it, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { LandingAuth } from "./landing-auth"

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
  }),
}))

describe("LandingAuth", () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it("renders sign in and register tabs", () => {
    render(<LandingAuth />)
    expect(screen.getByRole("tab", { name: /sign in/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /register/i })).toBeInTheDocument()
  })

  it("shows email and password fields in login mode by default", () => {
    render(<LandingAuth />)
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
  })

  it("does not show full name field in login mode", () => {
    render(<LandingAuth />)
    expect(screen.queryByLabelText(/full name/i)).not.toBeInTheDocument()
  })

  it("renders the submit button with sign in label in login mode", () => {
    render(<LandingAuth />)
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument()
  })

  it("shows full name and role fields after switching to register tab", async () => {
    const user = userEvent.setup()
    render(<LandingAuth />)
    await user.click(screen.getByRole("tab", { name: /register/i }))
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/role/i)).toBeInTheDocument()
  })

  it("renders register submit button after tab switch", async () => {
    const user = userEvent.setup()
    render(<LandingAuth />)
    await user.click(screen.getByRole("tab", { name: /register/i }))
    expect(screen.getByRole("button", { name: /register/i })).toBeInTheDocument()
  })
})
