import { beforeEach, describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { AttemptsTable } from "./AttemptsTable"
import { ChartWrapper } from "./ChartWrapper"
import { SummaryHeader } from "./SummaryHeader"
import { SectionErrorBoundary } from "./SectionErrorBoundary"
import { SectionErrorFallback } from "./SectionErrorFallback"
import { AttemptStatus, type Attempt, type UserReportSummary } from "@/lib/api/types"

const refresh = vi.fn()
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}))

beforeEach(() => {
  refresh.mockClear()
})

const attempts: Attempt[] = [
  {
    session_id: "sess-1",
    user_id: 1,
    test_id: "t1",
    status: AttemptStatus.COMPLETED,
    score: 80,
    time_spent_seconds: 90,
    created_at: "2026-06-01T10:00:00Z",
  },
  {
    session_id: "sess-2",
    user_id: 1,
    test_id: "t1",
    status: AttemptStatus.ABANDONED,
    score: 40,
    time_spent_seconds: 200,
    created_at: "2026-06-02T10:00:00Z",
  },
]

const summary: UserReportSummary = {
  user_id: 1,
  total_attempts: 2,
  average_score: 60,
  best_score: 80,
  total_time_spent: 290,
  most_recent_attempt: attempts[1],
}

describe("SummaryHeader", () => {
  it("renders the headline score and elapsed time", () => {
    render(<SummaryHeader summary={summary} />)
    expect(screen.getByText("Best score")).toBeInTheDocument()
    expect(screen.getByText("80%")).toBeInTheDocument()
    // total_time_spent 290s -> 4m 50s
    expect(screen.getByText("4m 50s")).toBeInTheDocument()
  })
})

describe("AttemptsTable", () => {
  it("renders one row per attempt with status and score", () => {
    render(<AttemptsTable attempts={attempts} highlightSessionId="sess-2" />)
    expect(screen.getByText("COMPLETED")).toBeInTheDocument()
    expect(screen.getByText("ABANDONED")).toBeInTheDocument()
    expect(screen.getByText("80%")).toBeInTheDocument()
    expect(screen.getByText("40%")).toBeInTheDocument()
  })

  it("highlights the originating session", () => {
    render(<AttemptsTable attempts={attempts} highlightSessionId="sess-2" />)
    expect(screen.getByText("This session")).toBeInTheDocument()
  })

  it("shows an empty state when there are no attempts", () => {
    render(<AttemptsTable attempts={[]} />)
    expect(screen.getByText(/no attempts recorded/i)).toBeInTheDocument()
  })
})

describe("ChartWrapper", () => {
  it("exposes an accessible labelled chart region", () => {
    render(<ChartWrapper attempts={attempts} />)
    expect(
      screen.getByRole("img", { name: /bar chart of scores across 2 attempts/i }),
    ).toBeInTheDocument()
  })

  it("shows an empty state with no attempts", () => {
    render(<ChartWrapper attempts={[]} />)
    expect(screen.getByText(/no attempts to chart/i)).toBeInTheDocument()
  })
})

describe("SectionErrorBoundary", () => {
  it("renders children when there is no error", () => {
    render(
      <SectionErrorBoundary title="summary">
        <p>panel content</p>
      </SectionErrorBoundary>,
    )
    expect(screen.getByText("panel content")).toBeInTheDocument()
  })

  it("renders a retry affordance when a child throws", () => {
    const Boom = () => {
      throw new Error("kaboom")
    }
    render(
      <SectionErrorBoundary title="chart">
        <Boom />
      </SectionErrorBoundary>,
    )
    expect(screen.getByText(/couldn't load the chart/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument()
  })
})

describe("SectionErrorFallback", () => {
  it("refreshes the route on retry by default (server-fetch recovery)", async () => {
    const user = userEvent.setup()
    render(<SectionErrorFallback title="summary" />)
    await user.click(screen.getByRole("button", { name: /retry/i }))
    expect(refresh).toHaveBeenCalledTimes(1)
  })

  it("uses a custom onRetry when provided", async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()
    render(<SectionErrorFallback title="chart" onRetry={onRetry} />)
    await user.click(screen.getByRole("button", { name: /retry/i }))
    expect(onRetry).toHaveBeenCalledTimes(1)
    expect(refresh).not.toHaveBeenCalled()
  })
})
