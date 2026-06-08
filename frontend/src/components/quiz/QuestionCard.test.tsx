import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { QuizQuestion } from "@/lib/api/types";
import { QuestionCard } from "./QuestionCard";

const mcq: QuizQuestion = {
  question_id: "q1",
  question_text: "Which language runs natively in the browser?",
  question_type: "mcq",
  difficulty: "easy",
  options: [
    { option_id: 1, text: "Python" },
    { option_id: 2, text: "JavaScript" },
  ],
};

describe("QuestionCard", () => {
  it("shows the question number, difficulty and text", () => {
    render(
      <QuestionCard question={mcq} questionNumber={3} selectedAnswer={null} onAnswerChange={vi.fn()} />
    );
    expect(screen.getByText("Q3")).toBeInTheDocument();
    expect(screen.getByText("easy")).toBeInTheDocument();
    expect(screen.getByText(/runs natively in the browser/)).toBeInTheDocument();
  });

  it("dispatches mcq to a single-answer view with radio options", () => {
    render(
      <QuestionCard question={mcq} questionNumber={1} selectedAnswer={null} onAnswerChange={vi.fn()} />
    );
    expect(screen.getByText("Single Answer")).toBeInTheDocument();
    expect(screen.getByLabelText("Python")).toBeInTheDocument();
    expect(screen.getByLabelText("JavaScript")).toBeInTheDocument();
  });

  it("dispatches multi questions to the multiple-answers view", () => {
    render(
      <QuestionCard
        question={{ ...mcq, question_type: "multi" }}
        questionNumber={1}
        selectedAnswer={[]}
        onAnswerChange={vi.fn()}
      />
    );
    expect(screen.getByText("Multiple Answers")).toBeInTheDocument();
  });

  it("dispatches true_false questions to the true/false view", () => {
    render(
      <QuestionCard
        question={{ ...mcq, question_type: "true_false", options: undefined }}
        questionNumber={1}
        selectedAnswer={null}
        onAnswerChange={vi.fn()}
      />
    );
    expect(screen.getByText("True or False")).toBeInTheDocument();
  });
});
