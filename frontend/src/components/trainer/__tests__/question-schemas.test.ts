import { describe, expect, it } from "vitest";
import {
  ALLOWED_IMAGE_TYPES,
  MAX_IMAGE_BYTES,
  buildQuestionSchema,
  imageFileSchema,
} from "../question-form-utils";

// Minimal valid base shared by every question type (question_text ≥ 10 chars,
// 1–20 skills). Spread + override per test to exercise one rule at a time.
const validBase = {
  question_text: "What is the time complexity of binary search?",
  difficulty: "easy" as const,
  skills: ["algorithms"],
  tags: "",
  answer_explanation: "",
};

const twoOptions = [
  { text: "O(n)", is_correct: false },
  { text: "O(log n)", is_correct: true },
];

function pngFile(bytes: number) {
  return new File([new Uint8Array(bytes)], "diagram.png", { type: "image/png" });
}

describe("imageFileSchema", () => {
  it("accepts a png within the size limit", () => {
    expect(imageFileSchema.safeParse(pngFile(1024)).success).toBe(true);
  });

  it("accepts a jpeg within the size limit", () => {
    const jpg = new File([new Uint8Array(1024)], "d.jpg", { type: "image/jpeg" });
    expect(imageFileSchema.safeParse(jpg).success).toBe(true);
  });

  it("rejects a disallowed mime type", () => {
    const gif = new File([new Uint8Array(1024)], "d.gif", { type: "image/gif" });
    const result = imageFileSchema.safeParse(gif);
    expect(result.success).toBe(false);
    expect(ALLOWED_IMAGE_TYPES).toEqual(["image/png", "image/jpeg"]);
  });

  it("rejects a file larger than MAX_IMAGE_BYTES", () => {
    expect(imageFileSchema.safeParse(pngFile(MAX_IMAGE_BYTES + 1)).success).toBe(false);
  });

  it("accepts a file exactly at the limit", () => {
    expect(imageFileSchema.safeParse(pngFile(MAX_IMAGE_BYTES)).success).toBe(true);
  });
});

describe("buildQuestionSchema — baseSchema rules", () => {
  const schema = buildQuestionSchema("create", "mcq");

  it("rejects question_text shorter than 10 characters", () => {
    const result = schema.safeParse({ ...validBase, question_text: "too short", options: twoOptions });
    expect(result.success).toBe(false);
  });

  it("requires at least one skill", () => {
    const result = schema.safeParse({ ...validBase, skills: [], options: twoOptions });
    expect(result.success).toBe(false);
  });

  it("rejects more than 20 skills", () => {
    const skills = Array.from({ length: 21 }, (_, i) => `skill-${i}`);
    const result = schema.safeParse({ ...validBase, skills, options: twoOptions });
    expect(result.success).toBe(false);
  });

  it("rejects an invalid difficulty enum value", () => {
    const result = schema.safeParse({ ...validBase, difficulty: "trivial", options: twoOptions });
    expect(result.success).toBe(false);
  });

  it("treats difficulty as optional", () => {
    const noDifficulty = { ...validBase, difficulty: undefined };
    const result = schema.safeParse({ ...noDifficulty, options: twoOptions });
    expect(result.success).toBe(true);
  });

  it("transforms a comma-separated tags string into a trimmed array", () => {
    const result = schema.safeParse({ ...validBase, tags: "math, search ,trees", options: twoOptions });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.tags).toEqual(["math", "search", "trees"]);
    }
  });
});

describe("buildQuestionSchema — create mcq (createOptionsSchema)", () => {
  const schema = buildQuestionSchema("create", "mcq");

  it("accepts 2–5 options with at least one correct", () => {
    expect(schema.safeParse({ ...validBase, options: twoOptions }).success).toBe(true);
  });

  it("accepts multiple correct options (mcq promotes to multi at submit)", () => {
    const options = [
      { text: "a", is_correct: true },
      { text: "b", is_correct: true },
    ];
    expect(schema.safeParse({ ...validBase, options }).success).toBe(true);
  });

  it("rejects fewer than 2 options", () => {
    const result = schema.safeParse({ ...validBase, options: [{ text: "a", is_correct: true }] });
    expect(result.success).toBe(false);
  });

  it("rejects more than 5 options", () => {
    const options = Array.from({ length: 6 }, (_, i) => ({ text: `o${i}`, is_correct: i === 0 }));
    expect(schema.safeParse({ ...validBase, options }).success).toBe(false);
  });

  it("rejects when no option is marked correct", () => {
    const options = [
      { text: "a", is_correct: false },
      { text: "b", is_correct: false },
    ];
    expect(schema.safeParse({ ...validBase, options }).success).toBe(false);
  });

  it("rejects an empty option text", () => {
    const options = [
      { text: "", is_correct: true },
      { text: "b", is_correct: false },
    ];
    expect(schema.safeParse({ ...validBase, options }).success).toBe(false);
  });
});

describe("buildQuestionSchema — edit mcq (editMcqSchema)", () => {
  const schema = buildQuestionSchema("edit", "mcq");

  it("accepts exactly one correct option", () => {
    expect(schema.safeParse({ ...validBase, options: twoOptions }).success).toBe(true);
  });

  it("rejects more than one correct option", () => {
    const options = [
      { text: "a", is_correct: true },
      { text: "b", is_correct: true },
    ];
    expect(schema.safeParse({ ...validBase, options }).success).toBe(false);
  });

  it("rejects zero correct options", () => {
    const options = [
      { text: "a", is_correct: false },
      { text: "b", is_correct: false },
    ];
    expect(schema.safeParse({ ...validBase, options }).success).toBe(false);
  });
});

describe("buildQuestionSchema — edit multi (editMultiSchema)", () => {
  const schema = buildQuestionSchema("edit", "multi");

  it("accepts at least one correct but not all correct", () => {
    const options = [
      { text: "a", is_correct: true },
      { text: "b", is_correct: false },
      { text: "c", is_correct: true },
    ];
    expect(schema.safeParse({ ...validBase, options }).success).toBe(true);
  });

  it("rejects when every option is correct", () => {
    const options = [
      { text: "a", is_correct: true },
      { text: "b", is_correct: true },
    ];
    expect(schema.safeParse({ ...validBase, options }).success).toBe(false);
  });

  it("rejects when no option is correct", () => {
    const options = [
      { text: "a", is_correct: false },
      { text: "b", is_correct: false },
    ];
    expect(schema.safeParse({ ...validBase, options }).success).toBe(false);
  });
});

describe("buildQuestionSchema — create multi (createMultiSchema)", () => {
  const schema = buildQuestionSchema("create", "multi");

  it("accepts at least one correct but not all correct", () => {
    const options = [
      { text: "a", is_correct: true },
      { text: "b", is_correct: false },
      { text: "c", is_correct: true },
    ];
    expect(schema.safeParse({ ...validBase, options }).success).toBe(true);
  });

  it("accepts a single correct option", () => {
    expect(schema.safeParse({ ...validBase, options: twoOptions }).success).toBe(true);
  });

  it("rejects when every option is correct", () => {
    const options = [
      { text: "a", is_correct: true },
      { text: "b", is_correct: true },
    ];
    expect(schema.safeParse({ ...validBase, options }).success).toBe(false);
  });

  it("rejects when no option is correct", () => {
    const options = [
      { text: "a", is_correct: false },
      { text: "b", is_correct: false },
    ];
    expect(schema.safeParse({ ...validBase, options }).success).toBe(false);
  });

  it("rejects fewer than 2 options", () => {
    expect(schema.safeParse({ ...validBase, options: [{ text: "a", is_correct: true }] }).success).toBe(false);
  });

  it("rejects more than 5 options", () => {
    const options = Array.from({ length: 6 }, (_, i) => ({ text: `o${i}`, is_correct: i === 0 }));
    expect(schema.safeParse({ ...validBase, options }).success).toBe(false);
  });
});

describe("buildQuestionSchema — true_false (trueFalseSchema)", () => {
  const schema = buildQuestionSchema("create", "true_false");

  it("accepts a boolean answer", () => {
    expect(schema.safeParse({ ...validBase, true_false_answer: true }).success).toBe(true);
  });

  it("rejects a missing answer", () => {
    expect(schema.safeParse({ ...validBase }).success).toBe(false);
  });

  it("rejects a non-boolean answer", () => {
    expect(schema.safeParse({ ...validBase, true_false_answer: "yes" }).success).toBe(false);
  });
});

describe("buildQuestionSchema — text (textSchema)", () => {
  const schema = buildQuestionSchema("create", "text");

  it("accepts a sample answer of at least 10 characters", () => {
    const result = schema.safeParse({ ...validBase, sample_answer: "A binary search halves the range." });
    expect(result.success).toBe(true);
  });

  it("rejects a sample answer shorter than 10 characters", () => {
    expect(schema.safeParse({ ...validBase, sample_answer: "short" }).success).toBe(false);
  });
});
