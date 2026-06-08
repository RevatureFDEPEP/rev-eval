import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { QuizQuestion } from "@/lib/api/types";
import { MultiQuestion } from "./MultiQuestion";

const question: QuizQuestion = {
  question_id: "q1",
  question_text: "Select all compiled languages.",
  question_type: "multi",
  difficulty: "medium",
  options: [
    { option_id: 1, text: "Rust" },
    { option_id: 2, text: "Python" },
    { option_id: 3, text: "Go" },
  ],
};

describe("MultiQuestion", () => {
  it("adds an option_id to the selection when toggled on", () => {
    const onAnswerChange = vi.fn();
    render(
      <MultiQuestion question={question} selectedAnswers={[]} onAnswerChange={onAnswerChange} />
    );
    fireEvent.click(screen.getByLabelText("Rust"));
    expect(onAnswerChange).toHaveBeenCalledWith([1]);
  });

  it("removes an already-selected option_id when toggled off", () => {
    const onAnswerChange = vi.fn();
    render(
      <MultiQuestion
        question={question}
        selectedAnswers={[1, 3]}
        onAnswerChange={onAnswerChange}
      />
    );
    fireEvent.click(screen.getByLabelText("Rust"));
    expect(onAnswerChange).toHaveBeenCalledWith([3]);
  });

  it("appends to existing selections without dropping them", () => {
    const onAnswerChange = vi.fn();
    render(
      <MultiQuestion
        question={question}
        selectedAnswers={[1]}
        onAnswerChange={onAnswerChange}
      />
    );
    fireEvent.click(screen.getByLabelText("Go"));
    expect(onAnswerChange).toHaveBeenCalledWith([1, 3]);
  });

  it("shows an error when there are no options", () => {
    render(
      <MultiQuestion
        question={{ ...question, options: undefined }}
        selectedAnswers={[]}
        onAnswerChange={vi.fn()}
      />
    );
    expect(screen.getByText(/No options available/i)).toBeInTheDocument();
  });
});
