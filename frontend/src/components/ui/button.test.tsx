import { describe, expect, it } from "@jest/globals"
import { render, screen } from "@testing-library/react"

import { Button } from "./button"

describe("Button", () => {
  it("renders button text", () => {
    render(<Button>Save changes</Button>)

    expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument()
  })

  it("renders variant and size selections as an accessible button", () => {
    render(
      <Button variant="secondary" size="lg">
        Continue
      </Button>
    )

    const button = screen.getByRole("button", { name: /continue/i })

    expect(button).toBeEnabled()
  })
})
