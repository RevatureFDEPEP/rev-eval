import * as z from "zod";

import type {
  QuestionCreate,
  QuestionDifficulty,
  QuestionType,
} from "@/lib/api/types";

export type QuestionFormType = Extract<QuestionType, "mcq" | "true_false" | "text">;

const tagsSchema = z.string().optional();

const baseSchema = {
  question_text: z
    .string()
    .min(10, "Question must be at least 10 characters"),
  difficulty: z.enum(["easy", "medium", "hard"]).optional(),
  skills: z
    .array(z.string())
    .min(1, "Select at least one skill")
    .max(20, "Maximum 20 skills allowed"),
  tags: tagsSchema,
  answer_explanation: z.string().optional(),
};

export const mcqSchema = z
  .object({
    ...baseSchema,
    options: z.array(
      z.object({
        text: z.string().min(1, "Option text is required"),
        is_correct: z.boolean(),
      })
    ),
  })
  .refine(
    (data) => {
      if (data.options.length < 2 || data.options.length > 5) {
        return false;
      }
      return data.options.some((opt) => opt.is_correct);
    },
    {
      message: "MCQ questions require 2-5 options with at least one marked correct",
      path: ["options"],
    }
  );

export const trueFalseSchema = z.object({
  ...baseSchema,
  true_false_answer: z.boolean(),
});

export const textSchema = z.object({
  ...baseSchema,
  sample_answer: z
    .string()
    .min(10, "Sample answer must be at least 10 characters"),
});

export type McqFormValues = z.output<typeof mcqSchema>;
export type TrueFalseFormValues = z.output<typeof trueFalseSchema>;
export type TextFormValues = z.output<typeof textSchema>;

export interface QuestionFormValues {
  question_text: string;
  difficulty?: QuestionDifficulty;
  skills: string[];
  tags?: string;
  answer_explanation?: string;
  options?: { text: string; is_correct: boolean }[];
  true_false_answer?: boolean;
  sample_answer?: string;
}

export interface QuestionDefaultValues {
  question_text: string;
  difficulty?: QuestionDifficulty;
  skills: string[];
  tags: string;
  answer_explanation: string;
  options?: { text: string; is_correct: boolean }[];
  true_false_answer?: boolean;
  sample_answer?: string;
}

export function getQuestionFormSchema(questionType: QuestionType) {
  switch (questionType) {
    case "true_false":
      return trueFalseSchema;
    case "text":
      return textSchema;
    case "mcq":
    case "multi":
    default:
      return mcqSchema;
  }
}

export function getQuestionDefaultValues(
  questionType: QuestionType
): QuestionDefaultValues {
  const base = {
    question_text: "",
    difficulty: undefined,
    skills: [],
    tags: "",
    answer_explanation: "",
  };

  switch (questionType) {
    case "true_false":
      return {
        ...base,
        true_false_answer: undefined,
      };
    case "text":
      return {
        ...base,
        sample_answer: "",
      };
    case "mcq":
    case "multi":
    default:
      return {
        ...base,
        options: [
          { text: "", is_correct: false },
          { text: "", is_correct: false },
        ],
      };
  }
}

export function transformQuestionFormData(
  values: QuestionFormValues,
  questionType: QuestionType
): QuestionCreate {
  let actualType: QuestionType = questionType;
  let correct_answers: (number | boolean | string)[] | undefined;
  let options: { text: string }[] | undefined;

  if (questionType === "mcq" || questionType === "multi") {
    if (!values.options) {
      throw new Error("MCQ form values require options");
    }

    const correctAnswerIndices = values.options
      .map((opt, idx) => (opt.is_correct ? idx + 1 : null))
      .filter((id): id is number => id !== null);

    if (correctAnswerIndices.length === 1) {
      actualType = "mcq";
    } else if (correctAnswerIndices.length > 1) {
      actualType = "multi";
    }

    correct_answers = correctAnswerIndices;
    options = values.options.map((opt) => ({ text: opt.text }));
  } else if (questionType === "true_false") {
    if (typeof values.true_false_answer !== "boolean") {
      throw new Error("True/false form values require true_false_answer");
    }

    correct_answers = [values.true_false_answer];
  }

  return {
    type: actualType,
    question_text: values.question_text,
    difficulty: values.difficulty,
    skills: values.skills,
    tags: values.tags ? values.tags.split(",").map((tag) => tag.trim()).filter(Boolean) : [],
    options,
    correct_answers,
    sample_answer: values.sample_answer || undefined,
    answer_explanation: values.answer_explanation || undefined,
  };
}
