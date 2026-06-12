import { describe, expect, it } from "vitest"
import { render, screen } from "@testing-library/react"
import { Button } from "./button"

describe("Button", () => {
  it("renders button text", () => {
    render(<Button>Save changes</Button>)
    expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument()
  })

  it("renders as an enabled button by default", () => {
    render(<Button>Submit</Button>)
    expect(screen.getByRole("button", { name: /submit/i })).toBeEnabled()
  })

  it("renders variant and size as an accessible button", () => {
    render(
      <Button variant="secondary" size="lg">
        Continue
      </Button>
    )
    const button = screen.getByRole("button", { name: /continue/i })
    expect(button).toBeEnabled()
  })

  it("renders as disabled when disabled prop is set", () => {
    render(<Button disabled>Disabled</Button>)
    expect(screen.getByRole("button", { name: /disabled/i })).toBeDisabled()
  })

  it("renders destructive variant", () => {
    render(<Button variant="destructive">Delete</Button>)
    expect(screen.getByRole("button", { name: /delete/i })).toBeInTheDocument()
  })
})
