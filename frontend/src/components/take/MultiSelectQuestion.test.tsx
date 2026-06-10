import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { SanitizedQuestion } from "@/lib/api/types";
import { MultiSelectQuestion } from "./MultiSelectQuestion";

const question: SanitizedQuestion = {
  id: "q2",
  type: "multi",
  question_text: "Which of these are JavaScript runtimes?",
  difficulty: "medium",
  options: [
    { option_id: 1, text: "Node.js" },
    { option_id: 2, text: "Deno" },
    { option_id: 3, text: "CPython" },
  ],
};

describe("MultiSelectQuestion", () => {
  it("renders every option's text", () => {
    render(<MultiSelectQuestion question={question} selected={[]} onChange={vi.fn()} />);
    expect(screen.getByText("Node.js")).toBeInTheDocument();
    expect(screen.getByText("Deno")).toBeInTheDocument();
    expect(screen.getByText("CPython")).toBeInTheDocument();
  });

  it("adds an option_id when an unchecked box is clicked", () => {
    const onChange = vi.fn();
    render(<MultiSelectQuestion question={question} selected={[1]} onChange={onChange} />);
    fireEvent.click(screen.getByLabelText("Deno"));
    expect(onChange).toHaveBeenCalledWith([1, 2]);
  });

  it("removes an option_id when a checked box is clicked", () => {
    const onChange = vi.fn();
    render(<MultiSelectQuestion question={question} selected={[1, 2]} onChange={onChange} />);
    fireEvent.click(screen.getByLabelText("Node.js"));
    expect(onChange).toHaveBeenCalledWith([2]);
  });
});
