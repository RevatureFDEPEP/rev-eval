import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { QuizQuestion } from "@/lib/api/types";
import { MCQQuestion } from "./MCQQuestion";

const question: QuizQuestion = {
  question_id: "q1",
  question_text: "Which language runs natively in the browser?",
  question_type: "mcq",
  difficulty: "easy",
  options: [
    { option_id: 1, text: "Python" },
    { option_id: 2, text: "JavaScript" },
    { option_id: 3, text: "Go" },
  ],
};

describe("MCQQuestion", () => {
  it("renders every option's text", () => {
    render(<MCQQuestion question={question} selectedAnswer={null} onAnswerChange={vi.fn()} />);
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("JavaScript")).toBeInTheDocument();
    expect(screen.getByText("Go")).toBeInTheDocument();
  });

  it("reports the chosen option_id when an option is clicked", () => {
    const onAnswerChange = vi.fn();
    render(
      <MCQQuestion question={question} selectedAnswer={null} onAnswerChange={onAnswerChange} />
    );
    fireEvent.click(screen.getByLabelText("JavaScript"));
    expect(onAnswerChange).toHaveBeenCalledWith(2);
  });

  it("shows an error when the question has no options", () => {
    render(
      <MCQQuestion
        question={{ ...question, options: [] }}
        selectedAnswer={null}
        onAnswerChange={vi.fn()}
      />
    );
    expect(screen.getByText(/No options available/i)).toBeInTheDocument();
  });
});
