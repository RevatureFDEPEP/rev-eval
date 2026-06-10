import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { SanitizedQuestion } from "@/lib/api/types";
import { SingleSelectQuestion } from "./SingleSelectQuestion";

const question: SanitizedQuestion = {
  id: "q1",
  type: "mcq",
  question_text: "Which language runs natively in the browser?",
  difficulty: "easy",
  options: [
    { option_id: 1, text: "Python" },
    { option_id: 2, text: "JavaScript" },
    { option_id: 3, text: "Go" },
  ],
};

describe("SingleSelectQuestion", () => {
  it("renders every option's text", () => {
    render(<SingleSelectQuestion question={question} selected={[]} onChange={vi.fn()} />);
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("JavaScript")).toBeInTheDocument();
    expect(screen.getByText("Go")).toBeInTheDocument();
  });

  it("reports the chosen option_id as a one-element array", () => {
    const onChange = vi.fn();
    render(<SingleSelectQuestion question={question} selected={[]} onChange={onChange} />);
    fireEvent.click(screen.getByLabelText("JavaScript"));
    expect(onChange).toHaveBeenCalledWith([2]);
  });

  it("shows an error when the question has no options", () => {
    render(
      <SingleSelectQuestion
        question={{ ...question, options: [] }}
        selected={[]}
        onChange={vi.fn()}
      />
    );
    expect(screen.getByText(/No options available/i)).toBeInTheDocument();
  });
});
