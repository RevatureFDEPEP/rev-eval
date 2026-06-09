import { describe, expect, it } from "vitest";
import { Question } from "@/lib/api";
import {
  buildQuestionSchema,
  getDefaultValues,
  toInitial,
  transformFormData,
} from "../question-form-utils";

const baseQuestion: Omit<Question, "type"> = {
  id: "abc123",
  question_text: "What does HTTP stand for in networking?",
  skills: ["Networking"],
  tags: ["http", "basics"],
  difficulty: "easy",
  answer_explanation: "It is the protocol of the web.",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const validFormBase = {
  question_text: "What does HTTP stand for in networking?",
  difficulty: "easy" as const,
  skills: ["Networking"],
  tags: "http, basics",
  answer_explanation: "",
};

describe("toInitial", () => {
  it("maps mcq options with is_correct keyed off option_id", () => {
    const q: Question = {
      ...baseQuestion,
      type: "mcq",
      options: [
        { option_id: 1, text: "Apple" },
        { option_id: 2, text: "Banana" },
        { option_id: 3, text: "Cherry" },
      ],
      correct_answers: [2],
    };
    const { type, data } = toInitial(q);
    expect(type).toBe("mcq");
    expect(data.options).toEqual([
      { text: "Apple", is_correct: false },
      { text: "Banana", is_correct: true },
      { text: "Cherry", is_correct: false },
    ]);
  });

  it("maps multi questions with multiple correct options", () => {
    const q: Question = {
      ...baseQuestion,
      type: "multi",
      options: [
        { option_id: 1, text: "A" },
        { option_id: 2, text: "B" },
        { option_id: 3, text: "C" },
      ],
      correct_answers: [1, 3],
    };
    const { type, data } = toInitial(q);
    expect(type).toBe("multi");
    expect(data.options?.map((o) => o.is_correct)).toEqual([
      true,
      false,
      true,
    ]);
  });

  it("extracts the boolean answer for true_false questions", () => {
    const q: Question = {
      ...baseQuestion,
      type: "true_false",
      correct_answers: [false],
    };
    const { type, data } = toInitial(q);
    expect(type).toBe("true_false");
    expect(data.true_false_answer).toBe(false);
    expect(data.options).toBeUndefined();
  });

  it("maps text questions with sample_answer", () => {
    const q: Question = {
      ...baseQuestion,
      type: "text",
      sample_answer: "Hypertext Transfer Protocol",
    };
    const { type, data } = toInitial(q);
    expect(type).toBe("text");
    expect(data.sample_answer).toBe("Hypertext Transfer Protocol");
  });

  it("joins tags into a comma string and defaults missing fields", () => {
    const q: Question = {
      ...baseQuestion,
      type: "text",
      tags: ["alpha", "beta"],
      answer_explanation: undefined,
      sample_answer: undefined,
    };
    const { data } = toInitial(q);
    expect(data.tags).toBe("alpha, beta");
    expect(data.answer_explanation).toBe("");
    expect(data.sample_answer).toBe("");
  });
});

describe("transformFormData — create mode", () => {
  it("promotes to multi when 2+ options are correct", () => {
    const result = transformFormData(
      {
        ...validFormBase,
        tags: ["http", "basics"], // post-zod-transform shape
        options: [
          { text: "A", is_correct: true },
          { text: "B", is_correct: true },
          { text: "C", is_correct: false },
        ],
      },
      "create",
      "mcq"
    );
    expect(result.type).toBe("multi");
    expect(result.correct_answers).toEqual([1, 2]);
    expect(result.options).toEqual([
      { text: "A" },
      { text: "B" },
      { text: "C" },
    ]);
  });

  it("keeps mcq when exactly one option is correct", () => {
    const result = transformFormData(
      {
        ...validFormBase,
        tags: [],
        options: [
          { text: "A", is_correct: false },
          { text: "B", is_correct: true },
        ],
      },
      "create",
      "mcq"
    );
    expect(result.type).toBe("mcq");
    expect(result.correct_answers).toEqual([2]);
  });

  it("keeps multi type with a single correct answer (no down-promote to mcq)", () => {
    const result = transformFormData(
      {
        ...validFormBase,
        tags: [],
        options: [
          { text: "A", is_correct: true },
          { text: "B", is_correct: false },
        ],
      },
      "create",
      "multi"
    );
    expect(result.type).toBe("multi");
    expect(result.correct_answers).toEqual([1]);
  });

  it("keeps multi type with several correct answers", () => {
    const result = transformFormData(
      {
        ...validFormBase,
        tags: [],
        options: [
          { text: "A", is_correct: true },
          { text: "B", is_correct: true },
          { text: "C", is_correct: false },
        ],
      },
      "create",
      "multi"
    );
    expect(result.type).toBe("multi");
    expect(result.correct_answers).toEqual([1, 2]);
  });

  it("sends boolean correct_answers and no options for true_false", () => {
    const result = transformFormData(
      { ...validFormBase, tags: [], true_false_answer: true },
      "create",
      "true_false"
    );
    expect(result.type).toBe("true_false");
    expect(result.correct_answers).toEqual([true]);
    expect(result.options).toBeUndefined();
  });

  it("sends no options or correct_answers for text", () => {
    const result = transformFormData(
      {
        ...validFormBase,
        tags: [],
        sample_answer: "Hypertext Transfer Protocol",
      },
      "create",
      "text"
    );
    expect(result.type).toBe("text");
    expect(result.options).toBeUndefined();
    expect(result.correct_answers).toBeUndefined();
    expect(result.sample_answer).toBe("Hypertext Transfer Protocol");
  });

  it("guards untransformed string tags to an empty array", () => {
    const result = transformFormData(
      { ...validFormBase, tags: "raw, string", true_false_answer: false },
      "create",
      "true_false"
    );
    expect(result.tags).toEqual([]);
  });
});

describe("transformFormData — edit mode", () => {
  it("does not promote mcq to multi even with 2+ correct", () => {
    const result = transformFormData(
      {
        ...validFormBase,
        tags: [],
        options: [
          { text: "A", is_correct: true },
          { text: "B", is_correct: true },
        ],
      },
      "edit",
      "mcq"
    );
    expect(result.type).toBe("mcq");
    expect(result.correct_answers).toEqual([1, 2]);
  });

  it("preserves multi type with a single correct answer", () => {
    const result = transformFormData(
      {
        ...validFormBase,
        tags: [],
        options: [
          { text: "A", is_correct: true },
          { text: "B", is_correct: false },
        ],
      },
      "edit",
      "multi"
    );
    expect(result.type).toBe("multi");
    expect(result.correct_answers).toEqual([1]);
  });
});

describe("buildQuestionSchema", () => {
  const options = (corrects: boolean[]) =>
    corrects.map((is_correct, i) => ({ text: `Option ${i + 1}`, is_correct }));

  it("create-mcq accepts one or many correct options (promotion path)", () => {
    const schema = buildQuestionSchema("create", "mcq");
    expect(
      schema.safeParse({ ...validFormBase, options: options([true, false]) })
        .success
    ).toBe(true);
    expect(
      schema.safeParse({
        ...validFormBase,
        options: options([true, true, false]),
      }).success
    ).toBe(true);
    expect(
      schema.safeParse({ ...validFormBase, options: options([false, false]) })
        .success
    ).toBe(false);
  });

  it("edit-mcq requires exactly one correct option", () => {
    const schema = buildQuestionSchema("edit", "mcq");
    expect(
      schema.safeParse({ ...validFormBase, options: options([true, false]) })
        .success
    ).toBe(true);
    expect(
      schema.safeParse({
        ...validFormBase,
        options: options([true, true, false]),
      }).success
    ).toBe(false);
    expect(
      schema.safeParse({ ...validFormBase, options: options([false, false]) })
        .success
    ).toBe(false);
  });

  it("edit-multi requires at least one but not all correct", () => {
    const schema = buildQuestionSchema("edit", "multi");
    expect(
      schema.safeParse({
        ...validFormBase,
        options: options([true, false, false]),
      }).success
    ).toBe(true);
    expect(
      schema.safeParse({
        ...validFormBase,
        options: options([true, true, false]),
      }).success
    ).toBe(true);
    expect(
      schema.safeParse({ ...validFormBase, options: options([false, false]) })
        .success
    ).toBe(false);
    expect(
      schema.safeParse({ ...validFormBase, options: options([true, true]) })
        .success
    ).toBe(false);
  });

  it("rejects question_text shorter than 10 characters", () => {
    const schema = buildQuestionSchema("create", "true_false");
    expect(
      schema.safeParse({
        ...validFormBase,
        question_text: "Too short",
        true_false_answer: true,
      }).success
    ).toBe(false);
  });

  it("rejects text questions with sample_answer shorter than 10 chars", () => {
    const schema = buildQuestionSchema("create", "text");
    expect(
      schema.safeParse({ ...validFormBase, sample_answer: "short" }).success
    ).toBe(false);
    expect(
      schema.safeParse({
        ...validFormBase,
        sample_answer: "Long enough sample answer",
      }).success
    ).toBe(true);
  });

  it("transforms the tags comma string into an array on parse", () => {
    const schema = buildQuestionSchema("create", "true_false");
    const parsed = schema.safeParse({
      ...validFormBase,
      tags: "alpha, beta",
      true_false_answer: false,
    });
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.tags).toEqual(["alpha", "beta"]);
    }
  });
});

describe("getDefaultValues", () => {
  it("seeds two empty options for mcq and multi", () => {
    expect(getDefaultValues("mcq").options).toHaveLength(2);
    expect(getDefaultValues("multi").options).toHaveLength(2);
  });

  it("seeds type-specific fields", () => {
    expect(getDefaultValues("true_false")).toHaveProperty(
      "true_false_answer",
      undefined
    );
    expect(getDefaultValues("text")).toHaveProperty("sample_answer", "");
  });
});
