import { describe, expect, it } from "@jest/globals"
import { render, screen } from "@testing-library/react"

import { Button } from "./button"

describe("Button", () => {
  it("renders button text", () => {
    render(<Button>Save changes</Button>)

    expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument()
  })

  it("applies the selected variant and size classes", () => {
    render(
      <Button variant="secondary" size="lg">
        Continue
      </Button>
    )

    const button = screen.getByRole("button", { name: /continue/i })

    expect(button).toHaveClass("bg-secondary")
    expect(button).toHaveClass("h-10")
  })
})
