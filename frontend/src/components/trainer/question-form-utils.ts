import * as z from "zod";
import { FieldValues } from "react-hook-form";
import {
  Question,
  QuestionCreate,
  QuestionDifficulty,
  QuestionType,
} from "@/lib/api";

export type QuestionFormMode = "create" | "edit";

// Pre-mapped form values used to seed the form in edit mode
export interface QuestionFormInitial {
  question_text: string;
  difficulty?: QuestionDifficulty;
  skills: string[];
  tags: string; // comma string for the input
  answer_explanation: string;
  options?: { text: string; is_correct: boolean }[]; // mcq/multi
  true_false_answer?: boolean; // true_false
  sample_answer?: string; // text
}

// Base fields common to all question types
const baseSchema = {
  question_text: z
    .string()
    .min(10, "Question must be at least 10 characters"),
  difficulty: z.enum(["easy", "medium", "hard"]).optional(),
  skills: z
    .array(z.string())
    .min(1, "Select at least one skill")
    .max(20, "Maximum 20 skills allowed"),
  tags: z
    .string()
    .optional()
    .transform((val) => (val ? val.split(",").map((t) => t.trim()) : [])),
  answer_explanation: z.string().optional(),
};

const optionsShape = z.array(
  z.object({
    text: z.string().min(1, "Option text is required"),
    is_correct: z.boolean(),
  })
);

// Create mode: 2-5 options, at least one correct (mcq auto-promotes to multi at submit)
const createOptionsSchema = z
  .object({ ...baseSchema, options: optionsShape })
  .refine(
    (data) => {
      if (data.options.length < 2 || data.options.length > 5) {
        return false;
      }
      return data.options.some((opt) => opt.is_correct);
    },
    {
      message:
        "MCQ questions require 2-5 options with at least one marked correct",
      path: ["options"],
    }
  );

// Edit mode, stored type mcq: exactly one correct (backend rejects otherwise)
const editMcqSchema = z
  .object({ ...baseSchema, options: optionsShape })
  .refine(
    (data) => {
      if (data.options.length < 2 || data.options.length > 5) {
        return false;
      }
      return data.options.filter((opt) => opt.is_correct).length === 1;
    },
    {
      message: "MCQ questions require 2-5 options with exactly one marked correct",
      path: ["options"],
    }
  );

// Edit mode, stored type multi: at least one correct, but not all (backend rules)
const editMultiSchema = z
  .object({ ...baseSchema, options: optionsShape })
  .refine(
    (data) => {
      if (data.options.length < 2 || data.options.length > 5) {
        return false;
      }
      const correctCount = data.options.filter((opt) => opt.is_correct).length;
      return correctCount >= 1 && correctCount < data.options.length;
    },
    {
      message:
        "Multi-select questions require at least one correct option, but not all options correct",
      path: ["options"],
    }
  );

const trueFalseSchema = z.object({
  ...baseSchema,
  true_false_answer: z.boolean(),
});

const textSchema = z.object({
  ...baseSchema,
  sample_answer: z
    .string()
    .min(10, "Sample answer must be at least 10 characters"),
});

export function buildQuestionSchema(
  mode: QuestionFormMode,
  questionType: QuestionType
) {
  switch (questionType) {
    case "mcq":
      return mode === "edit" ? editMcqSchema : createOptionsSchema;
    case "multi":
      // Create flow never starts as "multi" (mcq promotes at submit), but
      // edit loads stored multi questions into the same options form.
      return mode === "edit" ? editMultiSchema : createOptionsSchema;
    case "true_false":
      return trueFalseSchema;
    case "text":
      return textSchema;
    default:
      return createOptionsSchema;
  }
}

export function getDefaultValues(questionType: QuestionType): FieldValues {
  const base = {
    question_text: "",
    difficulty: undefined,
    skills: [],
    tags: "",
    answer_explanation: "",
  };

  switch (questionType) {
    case "mcq":
    case "multi":
      return {
        ...base,
        options: [
          { text: "", is_correct: false },
          { text: "", is_correct: false },
        ],
      };
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
    default:
      return base;
  }
}

export function transformFormData(
  values: FieldValues,
  mode: QuestionFormMode,
  questionType: QuestionType
): QuestionCreate {
  let actualType: QuestionType = questionType;
  let correct_answers: (number | boolean | string)[] | undefined = undefined;
  let options: { text: string }[] | undefined = undefined;

  if (questionType === "mcq" || questionType === "multi") {
    // Map checked options to 1-indexed option ids
    const correctAnswerIndices = values.options
      .map((opt: { is_correct?: boolean }, idx: number) =>
        opt.is_correct ? idx + 1 : null
      )
      .filter((id: number | null): id is number => id !== null);

    if (mode === "create") {
      // Create: determine if it's MCQ (1 answer) or MULTI (2+ answers)
      if (correctAnswerIndices.length === 1) {
        actualType = "mcq";
      } else if (correctAnswerIndices.length > 1) {
        actualType = "multi";
      }
    }
    // Edit: type is immutable on the backend — keep the stored type

    correct_answers = correctAnswerIndices;
    options = values.options.map((opt: { text: string }) => ({
      text: opt.text,
    }));
  } else if (questionType === "true_false") {
    // For TRUE_FALSE, send boolean in correct_answers, no options
    correct_answers = [values.true_false_answer];
    options = undefined;
  } else if (questionType === "text") {
    // For TEXT, no options or correct_answers
    correct_answers = undefined;
    options = undefined;
  }

  return {
    type: actualType,
    question_text: values.question_text,
    difficulty: values.difficulty,
    skills: values.skills,
    tags: typeof values.tags === "string" ? [] : values.tags || [],
    options,
    correct_answers,
    sample_answer: values.sample_answer || undefined,
    answer_explanation: values.answer_explanation || undefined,
  };
}

// Map a fetched question to form initial values for edit mode
export function toInitial(q: Question): {
  type: QuestionType;
  data: QuestionFormInitial;
} {
  const base = {
    question_text: q.question_text,
    difficulty: q.difficulty,
    skills: q.skills ?? [],
    tags: (q.tags ?? []).join(", "),
    answer_explanation: q.answer_explanation ?? "",
  };

  if (q.type === "mcq" || q.type === "multi") {
    const correct = new Set((q.correct_answers ?? []) as number[]); // 1-indexed option_ids
    return {
      type: q.type,
      data: {
        ...base,
        options: (q.options ?? []).map((o) => ({
          text: o.text,
          is_correct: correct.has(o.option_id),
        })),
      },
    };
  }

  if (q.type === "true_false") {
    return {
      type: "true_false",
      data: {
        ...base,
        true_false_answer: q.correct_answers?.[0] as boolean | undefined,
      },
    };
  }

  return {
    type: "text",
    data: { ...base, sample_answer: q.sample_answer ?? "" },
  };
}
