import { describe, expect, it } from "@jest/globals";

import {
  getQuestionDefaultValues,
  getQuestionFormSchema,
  mcqSchema,
  textSchema,
  transformQuestionFormData,
  trueFalseSchema,
  type McqFormValues,
  type TextFormValues,
  type TrueFalseFormValues,
} from "./question-form-schema";

const validMcqForm = {
  question_text: "Which keyword declares a block scoped variable?",
  difficulty: "easy",
  skills: ["JavaScript"],
  tags: "variables, scope",
  answer_explanation: "let is block scoped.",
  options: [
    { text: "var", is_correct: false },
    { text: "let", is_correct: true },
  ],
};

describe("question form schemas", () => {
  it("accepts a valid MCQ question", () => {
    const result = mcqSchema.safeParse(validMcqForm);

    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.tags).toBe("variables, scope");
    }
  });

  it("rejects MCQ questions without a correct answer", () => {
    const result = mcqSchema.safeParse({
      ...validMcqForm,
      options: [
        { text: "var", is_correct: false },
        { text: "let", is_correct: false },
      ],
    });

    expect(result.success).toBe(false);
  });

  it("rejects MCQ questions with fewer than two options", () => {
    const result = mcqSchema.safeParse({
      ...validMcqForm,
      options: [{ text: "let", is_correct: true }],
    });

    expect(result.success).toBe(false);
  });

  it("rejects MCQ questions with more than five options", () => {
    const result = mcqSchema.safeParse({
      ...validMcqForm,
      options: [
        { text: "one", is_correct: true },
        { text: "two", is_correct: false },
        { text: "three", is_correct: false },
        { text: "four", is_correct: false },
        { text: "five", is_correct: false },
        { text: "six", is_correct: false },
      ],
    });

    expect(result.success).toBe(false);
  });

  it("accepts true/false answers", () => {
    const result = trueFalseSchema.safeParse({
      question_text: "JavaScript is case-sensitive.",
      skills: ["JavaScript"],
      tags: "",
      answer_explanation: "",
      true_false_answer: true,
    });

    expect(result.success).toBe(true);
  });

  it("rejects short text sample answers", () => {
    const result = textSchema.safeParse({
      question_text: "Explain dependency injection in Angular.",
      skills: ["Angular"],
      tags: "",
      answer_explanation: "",
      sample_answer: "DI",
    });

    expect(result.success).toBe(false);
  });

  it("returns the expected schema for each question type", () => {
    expect(getQuestionFormSchema("mcq")).toBe(mcqSchema);
    expect(getQuestionFormSchema("multi")).toBe(mcqSchema);
    expect(getQuestionFormSchema("true_false")).toBe(trueFalseSchema);
    expect(getQuestionFormSchema("text")).toBe(textSchema);
  });

  it("returns default values by question type", () => {
    expect(getQuestionDefaultValues("mcq").options).toHaveLength(2);
    expect(getQuestionDefaultValues("true_false").true_false_answer).toBeUndefined();
    expect(getQuestionDefaultValues("text").sample_answer).toBe("");
  });
});

describe("transformQuestionFormData", () => {
  it("builds an MCQ payload for one correct answer", () => {
    const values = mcqSchema.parse(validMcqForm) as McqFormValues;

    expect(transformQuestionFormData(values, "mcq")).toEqual({
      type: "mcq",
      question_text: "Which keyword declares a block scoped variable?",
      difficulty: "easy",
      skills: ["JavaScript"],
      tags: ["variables", "scope"],
      options: [{ text: "var" }, { text: "let" }],
      correct_answers: [2],
      sample_answer: undefined,
      answer_explanation: "let is block scoped.",
    });
  });

  it("builds a multi payload for multiple correct answers", () => {
    const values = mcqSchema.parse({
      ...validMcqForm,
      options: [
        { text: "let", is_correct: true },
        { text: "const", is_correct: true },
      ],
    }) as McqFormValues;

    expect(transformQuestionFormData(values, "mcq").type).toBe("multi");
  });

  it("builds a true/false payload", () => {
    const values = trueFalseSchema.parse({
      question_text: "JavaScript is case-sensitive.",
      skills: ["JavaScript"],
      tags: "",
      answer_explanation: "",
      true_false_answer: false,
    }) as TrueFalseFormValues;

    expect(transformQuestionFormData(values, "true_false").correct_answers).toEqual([false]);
  });

  it("builds a text payload without options or correct answers", () => {
    const values = textSchema.parse({
      question_text: "Explain dependency injection in Angular.",
      skills: ["Angular"],
      tags: "angular",
      answer_explanation: "",
      sample_answer: "Dependency injection provides dependencies to classes.",
    }) as TextFormValues;

    expect(transformQuestionFormData(values, "text")).toEqual({
      type: "text",
      question_text: "Explain dependency injection in Angular.",
      difficulty: undefined,
      skills: ["Angular"],
      tags: ["angular"],
      options: undefined,
      correct_answers: undefined,
      sample_answer: "Dependency injection provides dependencies to classes.",
      answer_explanation: undefined,
    });
  });
});
