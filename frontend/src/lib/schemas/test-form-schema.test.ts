import { describe, expect, it } from "@jest/globals";

import { TestType } from "@/lib/api/types";

import { buildTestPayload, testFormSchema, type TestFormValues } from "./test-form-schema";

const validTestForm: TestFormValues = {
  name: "Java Foundations",
  role: "Associate",
  duration_minutes: 45,
  number_of_questions: 20,
  active: true,
  skill_ids: [1, 2],
};

describe("testFormSchema", () => {
  it("accepts a valid test form", () => {
    expect(testFormSchema.safeParse(validTestForm).success).toBe(true);
  });

  it("rejects short test names", () => {
    const result = testFormSchema.safeParse({ ...validTestForm, name: "JS" });

    expect(result.success).toBe(false);
  });

  it("rejects duration outside the allowed range", () => {
    expect(testFormSchema.safeParse({ ...validTestForm, duration_minutes: 4 }).success).toBe(false);
    expect(testFormSchema.safeParse({ ...validTestForm, duration_minutes: 241 }).success).toBe(false);
  });

  it("rejects question count outside the allowed range", () => {
    expect(testFormSchema.safeParse({ ...validTestForm, number_of_questions: 9 }).success).toBe(false);
    expect(testFormSchema.safeParse({ ...validTestForm, number_of_questions: 51 }).success).toBe(false);
  });

  it("requires at least one selected skill", () => {
    const result = testFormSchema.safeParse({ ...validTestForm, skill_ids: [] });

    expect(result.success).toBe(false);
  });
});

describe("buildTestPayload", () => {
  it("converts form minutes to API seconds for quizzes", () => {
    expect(buildTestPayload(validTestForm, "QUIZ")).toEqual({
      name: "Java Foundations",
      test_type: TestType.QUIZ,
      role: "Associate",
      duration_seconds: 2700,
      number_of_questions: 20,
      active: true,
      skill_ids: [1, 2],
    });
  });

  it("sets the interview test type", () => {
    expect(buildTestPayload(validTestForm, "INTERVIEW").test_type).toBe(TestType.INTERVIEW);
  });
});
