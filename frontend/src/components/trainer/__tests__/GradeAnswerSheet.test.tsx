import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { PendingAnswer } from "@/lib/api";

// Mock the grading API + toast so the test exercises only the component (W5-F1).
const gradeAnswer = vi.fn();
vi.mock("@/lib/api", () => ({
  gradeAnswer: (...args: unknown[]) => gradeAnswer(...args),
}));
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { GradeAnswerSheet } from "../GradeAnswerSheet";

const ANSWER: PendingAnswer = {
  answer_id: 7,
  session_id: "11111111-1111-1111-1111-111111111111",
  user_id: 42,
  question_index: 2,
  question_id: "q-mongo-id",
  submitted_answers: ["candidate prose"],
  submitted_at: "2026-06-10T10:00:00Z",
  test_id: 1,
  test_name: "Java Quiz",
  question_text: "Explain polymorphism.",
  sample_answer: "Same interface, many implementations.",
};

describe("GradeAnswerSheet", () => {
  beforeEach(() => {
    gradeAnswer.mockReset();
  });

  it("renders the pending answer with its question and submission", () => {
    render(
      <GradeAnswerSheet answer={ANSWER} open onOpenChange={() => {}} />,
    );
    expect(screen.getByText("Explain polymorphism.")).toBeInTheDocument();
    expect(screen.getByText("candidate prose")).toBeInTheDocument();
    expect(
      screen.getByText("Same interface, many implementations."),
    ).toBeInTheDocument();
  });

  it("submits the entered score + feedback via gradeAnswer", async () => {
    gradeAnswer.mockResolvedValue({});
    const onGraded = vi.fn();
    render(
      <GradeAnswerSheet
        answer={ANSWER}
        open
        onOpenChange={() => {}}
        onGraded={onGraded}
      />,
    );

    fireEvent.change(screen.getByLabelText("Score (0 to 1)"), {
      target: { value: "0.75" },
    });
    fireEvent.change(screen.getByLabelText("Feedback (optional)"), {
      target: { value: "solid" },
    });
    fireEvent.click(screen.getByRole("button", { name: /submit grade/i }));

    await waitFor(() => expect(gradeAnswer).toHaveBeenCalledTimes(1));
    expect(gradeAnswer).toHaveBeenCalledWith(ANSWER.session_id, 2, {
      score: 0.75,
      feedback: "solid",
    });
    await waitFor(() => expect(onGraded).toHaveBeenCalled());
  });
});
