import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Timer } from "./Timer";

const renderTimer = (overrides: Partial<Parameters<typeof Timer>[0]> = {}) => {
  const props = {
    timeRemaining: 600,
    formatTime: () => "10:00",
    isWarning: false,
    isCritical: false,
    ...overrides,
  };
  return render(<Timer {...props} />);
};

describe("Timer", () => {
  it("renders the formatted time string", () => {
    renderTimer({ formatTime: () => "09:42" });
    expect(screen.getByText("09:42")).toBeInTheDocument();
  });

  it("uses the calm (blue) style by default", () => {
    const { container } = renderTimer();
    const badge = container.querySelector(".font-mono");
    expect(badge?.className).toContain("text-blue-700");
    expect(badge?.className).not.toContain("animate-pulse");
  });

  it("uses the amber warning style when isWarning is set", () => {
    const { container } = renderTimer({ isWarning: true });
    const badge = container.querySelector(".font-mono");
    expect(badge?.className).toContain("text-amber-700");
  });

  it("uses the critical (pulsing red) style when isCritical is set", () => {
    const { container } = renderTimer({ isWarning: true, isCritical: true });
    const badge = container.querySelector(".font-mono");
    expect(badge?.className).toContain("text-red-700");
    expect(badge?.className).toContain("animate-pulse");
  });
});
