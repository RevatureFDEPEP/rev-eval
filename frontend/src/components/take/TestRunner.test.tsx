import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { AnswerResult, AuthIdentity, SanitizedQuestion, SessionOut } from "@/lib/api/types";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { ExamError } from "@/lib/exam/errors";
import { TestRunner } from "./TestRunner";

const identity: AuthIdentity = {
  user_id: 7,
  email: "candidate@example.com",
  role: "PARTICIPANT",
};

// Far-future window so the live countdown never expires during a test.
const session: SessionOut = {
  session_id: "s1",
  session_token: "tok",
  server_now: "2026-01-01T00:00:00Z",
  expires_at: "2026-01-01T01:00:00Z",
  current_index: 0,
  total_questions: 2,
  question: null,
};

const q1: SanitizedQuestion = {
  id: "q1",
  type: "mcq",
  question_text: "Q1: pick one",
  options: [
    { option_id: 1, text: "Python" },
    { option_id: 2, text: "JavaScript" },
  ],
};

const q2: SanitizedQuestion = {
  id: "q2",
  type: "multi",
  question_text: "Q2: pick many",
  options: [
    { option_id: 1, text: "Node.js" },
    { option_id: 2, text: "Deno" },
  ],
};

const noopSave = vi.fn().mockResolvedValue({});

function renderRunner(
  submitAnswerFn: (id: string, a: number[]) => Promise<AnswerResult>,
) {
  return render(
    <AuthProvider initialUser={identity}>
      <TestRunner
        session={{ ...session, question: q1 }}
        initialQuestions={[q1]}
        submitAnswerFn={submitAnswerFn}
        saveDraftFn={noopSave}
      />
    </AuthProvider>,
  );
}

const advanceResult: AnswerResult = {
  session_id: "s1",
  question_id: "q1",
  current_index: 1,
  total_questions: 2,
  status: "ACTIVE",
  next_question: q2,
};

const finalResult: AnswerResult = {
  session_id: "s1",
  question_id: "q2",
  current_index: 2,
  total_questions: 2,
  status: "SUBMITTED",
  submitted_at: "2026-01-01T00:05:00Z",
};

describe("TestRunner (W3-F4 exam client)", () => {
  it("seeds from session.question and shows identity + timer", () => {
    render(
      <AuthProvider initialUser={identity}>
        <TestRunner
          session={{ ...session, question: q1, total_questions: 1 }}
          submitAnswerFn={vi.fn()}
          saveDraftFn={noopSave}
        />
      </AuthProvider>,
    );
    expect(screen.getByText("Q1: pick one")).toBeInTheDocument();
    expect(screen.getByTestId("auth-identity")).toHaveTextContent(
      "candidate@example.com (PARTICIPANT)",
    );
    // Timer rendered from server timing (1h window → "60:00").
    expect(screen.getByText("60:00")).toBeInTheDocument();
  });

  it("submits the current answer, appends next_question, and advances", async () => {
    const submitFn = vi.fn().mockResolvedValue(advanceResult);
    renderRunner(submitFn);

    fireEvent.click(screen.getByLabelText("Python")); // q1 → [1]
    fireEvent.click(screen.getByTestId("submit-button"));

    await waitFor(() => expect(screen.getByText("Q2: pick many")).toBeInTheDocument());
    expect(submitFn).toHaveBeenCalledWith("s1", [1]);
    expect(screen.getByText("Question 2 of 2")).toBeInTheDocument();
  });

  it("finalizes on the last question and renders a locked confirmation", async () => {
    const submitFn = vi
      .fn()
      .mockResolvedValueOnce(advanceResult)
      .mockResolvedValueOnce(finalResult);
    renderRunner(submitFn);

    fireEvent.click(screen.getByLabelText("Python"));
    fireEvent.click(screen.getByTestId("submit-button"));
    await waitFor(() => screen.getByText("Q2: pick many"));

    expect(screen.getByTestId("submit-button")).toHaveTextContent("Submit Exam");
    fireEvent.click(screen.getByLabelText("Node.js"));
    fireEvent.click(screen.getByTestId("submit-button"));

    await waitFor(() => expect(screen.getByTestId("exam-confirmation")).toBeInTheDocument());
    expect(screen.getByText("Exam submitted")).toBeInTheDocument();
  });

  it("optimistically locks inputs + submit while a submission is in flight", async () => {
    // A never-resolving submit keeps the runner in the 'submitting' state.
    const submitFn = vi.fn(() => new Promise<AnswerResult>(() => {}));
    renderRunner(submitFn);

    fireEvent.click(screen.getByLabelText("Python"));
    fireEvent.click(screen.getByTestId("submit-button"));

    await waitFor(() =>
      expect(screen.getByRole("radio", { name: "Python" })).toBeDisabled(),
    );
    expect(screen.getByTestId("submit-button")).toBeDisabled();
    expect(screen.getByTestId("submit-button")).toHaveTextContent("Submitting…");
  });

  it("surfaces a semantic error and keeps inputs locked (halts)", async () => {
    const submitFn = vi.fn().mockRejectedValue(new ExamError("semantic", 422, "bad payload"));
    renderRunner(submitFn);

    fireEvent.click(screen.getByLabelText("Python"));
    fireEvent.click(screen.getByTestId("submit-button"));

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByRole("radio", { name: "Python" })).toBeDisabled();
  });

  // W3-F7 item 3 — a reused session restores autosaved drafts + true position.
  it("restores draft answers and offsets the question counter on a resumed session", () => {
    render(
      <AuthProvider initialUser={identity}>
        <TestRunner
          session={{
            ...session,
            question: q1,
            current_index: 1,
            total_questions: 3,
            draft_answers: { q1: [1] },
          }}
          submitAnswerFn={vi.fn()}
          saveDraftFn={noopSave}
        />
      </AuthProvider>,
    );
    expect(screen.getByText("Question 2 of 3")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Python" })).toBeChecked();
  });

  // W3-F7 item 2 — a transient outage must not brick the attempt.
  it("offers Retry submission after a transient failure and recovers on success", async () => {
    const submitFn = vi
      .fn()
      .mockRejectedValueOnce(new ExamError("transient", 503, "gateway down"))
      .mockResolvedValueOnce(advanceResult);
    renderRunner(submitFn);

    fireEvent.click(screen.getByLabelText("Python"));
    fireEvent.click(screen.getByTestId("submit-button"));

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    const retry = screen.getByTestId("retry-button");
    expect(retry).toHaveTextContent("Retry submission");

    fireEvent.click(retry);
    await waitFor(() => expect(screen.getByText("Q2: pick many")).toBeInTheDocument());
    expect(submitFn).toHaveBeenCalledTimes(2);
    // Recovered: inputs unlocked on the next live question.
    expect(screen.getByRole("checkbox", { name: "Node.js" })).not.toBeDisabled();
  });

  it("renders no retry affordance for a semantic rejection", async () => {
    const submitFn = vi.fn().mockRejectedValue(new ExamError("semantic", 409, "locked"));
    renderRunner(submitFn);

    fireEvent.click(screen.getByLabelText("Python"));
    fireEvent.click(screen.getByTestId("submit-button"));

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.queryByTestId("retry-button")).not.toBeInTheDocument();
  });

  it("reviews an answered question read-only and preserves its selection", async () => {
    const submitFn = vi.fn().mockResolvedValue(advanceResult);
    renderRunner(submitFn);

    fireEvent.click(screen.getByLabelText("Python")); // answer q1
    fireEvent.click(screen.getByTestId("submit-button"));
    await waitFor(() => screen.getByText("Q2: pick many"));

    // Go back to the answered q1 — read-only, selection preserved.
    fireEvent.click(screen.getByText("Previous"));
    expect(screen.getByText("Q1: pick one")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Python" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Python" })).toBeDisabled();

    // Next returns forward to the live question (local nav, no resubmit).
    fireEvent.click(screen.getByText("Next"));
    expect(screen.getByText("Q2: pick many")).toBeInTheDocument();
    expect(submitFn).toHaveBeenCalledTimes(1); // review navigation does not re-submit
  });
});
