import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { SanitizedQuestion } from "@/lib/api/types";
import { TrueFalseQuestion } from "./TrueFalseQuestion";

// Canonical option-less true_false doc (W2-F6 shape: correct_answers stored
// server-side as [true]/[false], no options exposed to the candidate).
const question: SanitizedQuestion = {
  id: "tf1",
  type: "true_false",
  question_text: "RAG combines retrieval with generation.",
  difficulty: "easy",
  options: null,
};

describe("TrueFalseQuestion", () => {
  it("renders True/False controls without an error for an option-less doc", () => {
    render(<TrueFalseQuestion question={question} selected={[]} onChange={vi.fn()} />);
    expect(screen.getByLabelText("True")).toBeInTheDocument();
    expect(screen.getByLabelText("False")).toBeInTheDocument();
    expect(screen.queryByText(/no options available/i)).not.toBeInTheDocument();
  });

  it("encodes True as option_id [1]", () => {
    const onChange = vi.fn();
    render(<TrueFalseQuestion question={question} selected={[]} onChange={onChange} />);
    fireEvent.click(screen.getByLabelText("True"));
    expect(onChange).toHaveBeenCalledWith([1]);
  });

  it("encodes False as option_id [0]", () => {
    const onChange = vi.fn();
    render(<TrueFalseQuestion question={question} selected={[]} onChange={onChange} />);
    fireEvent.click(screen.getByLabelText("False"));
    expect(onChange).toHaveBeenCalledWith([0]);
  });

  it("reflects the current selection ([1] → True checked)", () => {
    render(<TrueFalseQuestion question={question} selected={[1]} onChange={vi.fn()} />);
    expect(screen.getByLabelText("True")).toBeChecked();
    expect(screen.getByLabelText("False")).not.toBeChecked();
  });

  it("reflects the current selection ([0] → False checked)", () => {
    render(<TrueFalseQuestion question={question} selected={[0]} onChange={vi.fn()} />);
    expect(screen.getByLabelText("False")).toBeChecked();
    expect(screen.getByLabelText("True")).not.toBeChecked();
  });

  it("does not fire onChange when disabled", () => {
    const onChange = vi.fn();
    render(
      <TrueFalseQuestion question={question} selected={[]} onChange={onChange} disabled />
    );
    fireEvent.click(screen.getByLabelText("True"));
    expect(onChange).not.toHaveBeenCalled();
  });
});
