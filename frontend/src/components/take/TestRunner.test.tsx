import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { AuthIdentity, SanitizedQuestion, SessionOut } from "@/lib/api/types";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { TestRunner } from "./TestRunner";

const identity: AuthIdentity = {
  user_id: 7,
  email: "candidate@example.com",
  role: "PARTICIPANT",
};

const session: SessionOut = {
  session_id: "s1",
  session_token: "tok",
  server_now: "2026-01-01T00:00:00Z",
  expires_at: "2026-01-01T01:00:00Z",
  current_index: 0,
  total_questions: 3,
  question: null,
};

const questions: SanitizedQuestion[] = [
  {
    id: "q1",
    type: "mcq",
    question_text: "Q1: pick one",
    options: [
      { option_id: 1, text: "Python" },
      { option_id: 2, text: "JavaScript" },
    ],
  },
  {
    id: "q2",
    type: "multi",
    question_text: "Q2: pick many",
    options: [
      { option_id: 1, text: "Node.js" },
      { option_id: 2, text: "Deno" },
    ],
  },
  {
    id: "q3",
    type: "mcq",
    question_text: "Q3: pick one",
    options: [
      { option_id: 1, text: "Yes" },
      { option_id: 2, text: "No" },
    ],
  },
];

function renderRunner(initial: SanitizedQuestion[] = questions) {
  return render(
    <AuthProvider initialUser={identity}>
      <TestRunner session={session} initialQuestions={initial} />
    </AuthProvider>
  );
}

describe("TestRunner", () => {
  it("seeds from session.question when no list is supplied", () => {
    render(
      <AuthProvider initialUser={identity}>
        <TestRunner session={{ ...session, question: questions[0], total_questions: 1 }} />
      </AuthProvider>
    );
    expect(screen.getByText("Q1: pick one")).toBeInTheDocument();
  });

  it("shows identity from AuthContext and the progress header", () => {
    renderRunner();
    expect(screen.getByTestId("auth-identity")).toHaveTextContent(
      "candidate@example.com (PARTICIPANT)"
    );
    expect(screen.getByText("Question 1 of 3")).toBeInTheDocument();
  });

  it("dispatches to the right leaf component by question.type", () => {
    renderRunner();
    // Q1 is single-select (radio).
    expect(screen.getByRole("radio", { name: "Python" })).toBeInTheDocument();
    fireEvent.click(screen.getByText("Next"));
    // Q2 is multi-select (checkbox).
    expect(screen.getByRole("checkbox", { name: "Node.js" })).toBeInTheDocument();
  });

  it("clamps Prev at the first question and Next at the last", () => {
    renderRunner();
    expect(screen.getByText("Previous")).toBeDisabled();
    expect(screen.getByText("Next")).not.toBeDisabled();
    fireEvent.click(screen.getByText("Next"));
    fireEvent.click(screen.getByText("Next"));
    expect(screen.getByText("Question 3 of 3")).toBeInTheDocument();
    expect(screen.getByText("Next")).toBeDisabled();
    expect(screen.getByText("Previous")).not.toBeDisabled();
  });

  it("preserves answers in the Map across Next/Prev navigation", () => {
    renderRunner();
    // Answer Q1.
    fireEvent.click(screen.getByLabelText("JavaScript"));
    expect(screen.getByRole("radio", { name: "JavaScript" })).toBeChecked();
    // Navigate forward then back — selection must survive (no re-fetch, state only).
    fireEvent.click(screen.getByText("Next"));
    expect(screen.getByText("Q2: pick many")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Previous"));
    expect(screen.getByText("Q1: pick one")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "JavaScript" })).toBeChecked();
  });

  it("keeps per-question answers independent across questions", () => {
    renderRunner();
    fireEvent.click(screen.getByLabelText("JavaScript")); // Q1 = [2]
    fireEvent.click(screen.getByText("Next"));
    fireEvent.click(screen.getByLabelText("Node.js")); // Q2 = [1]
    fireEvent.click(screen.getByLabelText("Deno")); // Q2 = [1, 2]
    expect(screen.getByRole("checkbox", { name: "Node.js" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Deno" })).toBeChecked();
    fireEvent.click(screen.getByText("Previous"));
    // Q1 still only JavaScript.
    expect(screen.getByRole("radio", { name: "JavaScript" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Python" })).not.toBeChecked();
  });
});
