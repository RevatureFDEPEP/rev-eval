"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  useFieldArray,
  useForm,
  useWatch,
  type FieldPath,
  type Resolver,
} from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { ArrowLeft, Check, Plus, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  ApiError,
  createQuestion,
  getSkills,
  type QuestionCreate,
  type QuestionDifficulty,
  type QuestionType,
  type SkillInfo,
} from "@/lib/api";

type OptionFormValue = {
  text: string;
  is_correct: boolean;
};

type QuestionFormValues = {
  type: QuestionType;
  question_text: string;
  difficulty?: QuestionDifficulty;
  skills: string[];
  tags?: string;
  answer_explanation?: string;
  options: OptionFormValue[];
  true_false_answer?: boolean;
  sample_answer?: string;
};

type ServerIssue = {
  loc?: unknown;
  msg?: unknown;
  message?: unknown;
};

type QuestionAuthorFormProps = {
  initialType: QuestionType;
};

const QUESTION_TYPE_LABELS: Record<QuestionType, string> = {
  mcq: "Single Choice",
  multi: "Multiple Choice",
  true_false: "True/False",
  text: "Text Answer",
};

const QUESTION_TYPE_DESCRIPTIONS: Record<QuestionType, string> = {
  mcq: "One correct answer from multiple options",
  multi: "One or more correct answers from multiple options",
  true_false: "A simple true or false statement",
  text: "Free-form response with a sample answer",
};

const skillListContainerClass =
  "max-h-[55vh] overflow-x-hidden overflow-y-auto overscroll-contain rounded-lg border border-slate-200 bg-white";

function parseCommaList(value?: string): string[] {
  return (value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function hasDuplicates(values: string[]): boolean {
  const normalized = values.map((value) => value.toLowerCase());
  return normalized.length !== new Set(normalized).size;
}

const optionSchema = z.object({
  text: z
    .string()
    .trim()
    .min(1, "Option text is required")
    .max(500, "Option text must be 500 characters or fewer"),
  is_correct: z.boolean(),
});

const optionsSchema = z
  .array(optionSchema)
  .min(2, "At least 2 options are required")
  .max(10, "Maximum 10 options allowed")
  .superRefine((options, ctx) => {
    const optionTexts = options.map((option) => option.text.trim().toLowerCase());
    const duplicateText = optionTexts.find(
      (text, index) => text && optionTexts.indexOf(text) !== index,
    );

    if (!duplicateText) return;

    optionTexts.forEach((text, index) => {
      if (text === duplicateText) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Options must be unique",
          path: [index, "text"],
        });
      }
    });
  });

const baseQuestionFields = {
  question_text: z
    .string()
    .trim()
    .min(10, "Question must be at least 10 characters")
    .max(2000, "Question must be 2000 characters or fewer"),
  difficulty: z.enum(["easy", "medium", "hard"]).optional(),
  skills: z
    .array(z.string())
    .min(1, "Select at least one skill")
    .max(20, "Maximum 20 skills allowed"),
  tags: z
    .string()
    .optional()
    .refine((value) => parseCommaList(value).length <= 30, {
      message: "Maximum 30 tags allowed",
    })
    .refine((value) => !hasDuplicates(parseCommaList(value)), {
      message: "Tags must be unique",
    }),
  answer_explanation: z
    .string()
    .trim()
    .max(2000, "Explanation must be 2000 characters or fewer")
    .optional(),
};

const questionFormSchema = z
  .discriminatedUnion("type", [
    z.object({
      type: z.literal("mcq"),
      ...baseQuestionFields,
      options: optionsSchema,
    }),
    z.object({
      type: z.literal("multi"),
      ...baseQuestionFields,
      options: optionsSchema,
    }),
    z.object({
      type: z.literal("true_false"),
      ...baseQuestionFields,
      true_false_answer: z.boolean().optional(),
    }),
    z.object({
      type: z.literal("text"),
      ...baseQuestionFields,
      sample_answer: z
        .string()
        .trim()
        .min(10, "Sample answer must be at least 10 characters")
        .max(5000, "Sample answer must be 5000 characters or fewer"),
    }),
  ])
  .superRefine((data, ctx) => {
    if (data.type === "mcq") {
      const correctCount = data.options.filter((option) => option.is_correct).length;

      if (correctCount !== 1) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "MCQ questions must have exactly one correct answer",
          path: ["options"],
        });
      }
    }

    if (data.type === "multi") {
      const correctCount = data.options.filter((option) => option.is_correct).length;

      if (correctCount < 1) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "MULTI questions must have at least one correct answer",
          path: ["options"],
        });
      }

      if (correctCount === data.options.length) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "MULTI questions cannot have all options marked correct",
          path: ["options"],
        });
      }
    }

    if (data.type === "true_false" && typeof data.true_false_answer !== "boolean") {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Select whether the answer is true or false",
        path: ["true_false_answer"],
      });
    }
  });

function createDefaultOptions(): OptionFormValue[] {
  return [
    { text: "", is_correct: false },
    { text: "", is_correct: false },
  ];
}

function normalizeOptions(options?: OptionFormValue[]): OptionFormValue[] {
  const normalized =
    options && options.length >= 2
      ? options.slice(0, 10)
      : createDefaultOptions();

  return normalized.map((option) => ({
    text: option.text ?? "",
    is_correct: option.is_correct === true,
  }));
}

function enforceSingleCorrect(options: OptionFormValue[]): OptionFormValue[] {
  let foundCorrect = false;

  return options.map((option) => {
    if (!option.is_correct) return option;

    if (foundCorrect) {
      return { ...option, is_correct: false };
    }

    foundCorrect = true;
    return option;
  });
}

function getDefaultValues(type: QuestionType): QuestionFormValues {
  const base: QuestionFormValues = {
    type,
    question_text: "",
    difficulty: "medium",
    skills: [],
    tags: "",
    answer_explanation: "",
    options: [],
    true_false_answer: undefined,
    sample_answer: "",
  };
  if (type === "mcq" || type === "multi") {
    return { ...base, options: createDefaultOptions() };
  }
  return base;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function getIssueMessage(issue: ServerIssue): string {
  if (typeof issue.msg === "string") return issue.msg;
  if (typeof issue.message === "string") return issue.message;
  return "The server rejected this value.";
}

function extractServerIssues(payload: unknown): ServerIssue[] {
  if (typeof payload === "string") {
    try {
      return extractServerIssues(JSON.parse(payload));
    } catch {
      return payload ? [{ msg: payload }] : [];
    }
  }

  if (Array.isArray(payload)) {
    return payload.filter(isRecord) as ServerIssue[];
  }

  if (!isRecord(payload)) return [];

  if (Array.isArray(payload.detail)) {
    return payload.detail.filter(isRecord) as ServerIssue[];
  }

  if (isRecord(payload.detail) && Array.isArray(payload.detail.validation_errors)) {
    return payload.detail.validation_errors.filter(isRecord) as ServerIssue[];
  }

  if (Array.isArray(payload.validation_errors)) {
    return payload.validation_errors.filter(isRecord) as ServerIssue[];
  }

  if (typeof payload.detail === "string") {
    return [{ msg: payload.detail }];
  }

  if (typeof payload.error === "string") {
    return [{ msg: payload.error }];
  }

  return [];
}

function issueToFieldPath(
  issue: ServerIssue,
  type: QuestionType,
): FieldPath<QuestionFormValues> | null {
  if (!Array.isArray(issue.loc)) return null;

  const loc = issue.loc.filter((segment) => segment !== "body");
  const [field, index, nestedField] = loc;

  if (field === "correct_answers") {
    return type === "true_false" ? "true_false_answer" : "options";
  }

  if (field === "options" && typeof index === "number" && nestedField === "text") {
    return `options.${index}.text` as FieldPath<QuestionFormValues>;
  }

  if (field === "options") return "options";

  if (
    field === "type" ||
    field === "question_text" ||
    field === "difficulty" ||
    field === "skills" ||
    field === "tags" ||
    field === "answer_explanation" ||
    field === "sample_answer" ||
    field === "true_false_answer"
  ) {
    return field;
  }

  return null;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const issues = extractServerIssues(error.body);
    return issues[0] ? getIssueMessage(issues[0]) : error.message;
  }

  return error instanceof Error ? error.message : "Failed to create question";
}

function getOptionsErrorMessage(error: unknown): string | null {
  if (!isRecord(error)) return null;
  return typeof error.message === "string" ? error.message : null;
}

export function QuestionAuthorForm({ initialType }: QuestionAuthorFormProps) {
  const router = useRouter();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [loadingSkills, setLoadingSkills] = useState(true);
  const [skillsError, setSkillsError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const form = useForm<QuestionFormValues>({
    resolver: zodResolver(questionFormSchema) as Resolver<QuestionFormValues>,
    defaultValues: getDefaultValues(initialType),
    mode: "onBlur",
  });

  const { fields, append } = useFieldArray({
    control: form.control,
    name: "options",
  });

  const selectedType =
    useWatch({ control: form.control, name: "type" }) ?? initialType;
  const watchedOptions = useWatch({ control: form.control, name: "options" }) ?? [];
  const selectedSkills = useWatch({ control: form.control, name: "skills" }) ?? [];
  const correctIndex = watchedOptions.findIndex((option) => option.is_correct);
  const optionsErrorMessage = getOptionsErrorMessage(form.formState.errors.options);

  const filteredSkills = useMemo(() => {
    if (!searchQuery.trim()) return skills;

    const query = searchQuery.toLowerCase();
    return skills.filter((skill) => skill.name.toLowerCase().includes(query));
  }, [skills, searchQuery]);

  useEffect(() => {
    let cancelled = false;

    async function loadSkills() {
      try {
        const data = await getSkills();
        if (!cancelled) {
          setSkills(data);
          setSkillsError(null);
        }
      } catch (error) {
        console.error("Failed to load skills:", error);
        if (!cancelled) {
          setSkillsError("Unable to load skills. Try refreshing the page.");
        }
      } finally {
        if (!cancelled) {
          setLoadingSkills(false);
        }
      }
    }

    loadSkills();

    return () => {
      cancelled = true;
    };
  }, []);

  const handleTypeChange = (type: QuestionType) => {
    const currentValues = form.getValues();
    const normalizedOptions = normalizeOptions(currentValues.options);
    const options = type === "mcq" ? enforceSingleCorrect(normalizedOptions) : normalizedOptions;

    form.reset(
      {
        ...currentValues,
        type,
        options,
        true_false_answer:
          type === "true_false" ? currentValues.true_false_answer : undefined,
        sample_answer: type === "text" ? currentValues.sample_answer ?? "" : "",
      },
      {
        keepDirty: true,
        keepTouched: true,
      },
    );
    form.clearErrors();
    setSubmitError(null);
    router.replace(`/trainer/questions/create?type=${type}`, { scroll: false });
  };

  const setSingleCorrect = (index: number) => {
    const nextOptions = form.getValues("options").map((option, optionIndex) => ({
      ...option,
      is_correct: optionIndex === index,
    }));

    form.setValue("options", nextOptions, {
      shouldDirty: true,
      shouldValidate: true,
    });
  };

  const removeOption = (index: number) => {
    const current = form.getValues("options").filter((_, i) => i !== index);
    form.setValue("options", current, { shouldValidate: true, shouldDirty: true });
  };

  const transformFormData = (values: QuestionFormValues): QuestionCreate => {
    const basePayload = {
      type: values.type,
      question_text: values.question_text,
      difficulty: values.difficulty,
      skills: values.skills,
      tags: parseCommaList(values.tags),
      answer_explanation: values.answer_explanation?.trim() || undefined,
    };

    if (values.type === "mcq" || values.type === "multi") {
      return {
        ...basePayload,
        options: values.options.map((option) => ({ text: option.text.trim() })),
        correct_answers: values.options.reduce<number[]>((answers, option, index) => {
          if (option.is_correct) {
            answers.push(index + 1);
          }

          return answers;
        }, []),
      };
    }

    if (values.type === "true_false") {
      return {
        ...basePayload,
        correct_answers: [values.true_false_answer === true],
      };
    }

    return {
      ...basePayload,
      sample_answer: values.sample_answer?.trim() || undefined,
    };
  };

  const applyServerErrors = (error: ApiError): boolean => {
    const issues = extractServerIssues(error.body);
    let appliedFieldError = false;

    for (const issue of issues) {
      const fieldPath = issueToFieldPath(issue, form.getValues("type"));

      if (fieldPath) {
        form.setError(fieldPath, {
          type: "server",
          message: getIssueMessage(issue),
        });
        appliedFieldError = true;
      }
    }

    return appliedFieldError;
  };

  const onSubmit = async (values: QuestionFormValues) => {
    try {
      setSubmitError(null);
      form.clearErrors();

      const payload = transformFormData(values);
      const created = await createQuestion(payload);

      toast.success("Question created", {
        description: `Question ${created.id} has been added to the bank.`,
      });
      router.push("/trainer/questions");
    } catch (error) {
      console.error("Failed to create question:", error);

      const hasFieldErrors = error instanceof ApiError ? applyServerErrors(error) : false;
      const message = hasFieldErrors
        ? "Please fix the highlighted fields."
        : getErrorMessage(error);

      setSubmitError(message);
      toast.error("Failed to create question", {
        description: message,
      });
    }
  };

  return (
    <div className="container mx-auto max-w-4xl space-y-8 px-4 py-8">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.back()}
          className="shrink-0"
          aria-label="Go back"
        >
          <ArrowLeft className="size-4" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            Create New Question
          </h1>
          <p className="text-sm text-slate-500">
            {QUESTION_TYPE_LABELS[selectedType]} question
          </p>
        </div>
      </div>

      {submitError && (
        <Card className="border-red-200 bg-red-50/50">
          <CardContent className="py-4">
            <p className="text-sm text-red-600">{submitError}</p>
          </CardContent>
        </Card>
      )}

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Question Type</CardTitle>
              <CardDescription>
                Choose how learners will answer this question
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="type"
                render={({ field }) => (
                  <FormItem>
                    <Select
                      value={field.value}
                      onValueChange={(value) => handleTypeChange(value as QuestionType)}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select question type" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {Object.entries(QUESTION_TYPE_LABELS).map(([type, label]) => (
                          <SelectItem key={type} value={type}>
                            {label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      {QUESTION_TYPE_DESCRIPTIONS[selectedType]}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Question Text</CardTitle>
              <CardDescription>
                Enter the question that students will see
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="question_text"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Textarea
                        placeholder="Enter your question here..."
                        className="min-h-[120px]"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Minimum 10 characters required
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {(selectedType === "mcq" || selectedType === "multi") && (
            <Card>
              <CardHeader>
                <CardTitle>Answer Options</CardTitle>
                <CardDescription>
                  Add 2-10 options and mark the correct answer choices.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {selectedType === "mcq" ? (
                  <RadioGroup
                    value={correctIndex >= 0 ? String(correctIndex) : undefined}
                    onValueChange={(value) => setSingleCorrect(Number(value))}
                    className="space-y-3"
                  >
                    {fields.map((field, index) => (
                      <div
                        key={field.id}
                        className="flex items-start gap-3 rounded-lg border p-4"
                      >
                        <RadioGroupItem
                          value={String(index)}
                          className="mt-2"
                          aria-label={`Mark option ${index + 1} correct`}
                        />
                        <FormField
                          control={form.control}
                          name={`options.${index}.text`}
                          render={({ field }) => (
                            <FormItem className="flex-1">
                              <FormControl>
                                <Input
                                  placeholder={`Option ${index + 1}`}
                                  {...field}
                                />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        {fields.length > 2 && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            onClick={() => removeOption(index)}
                            aria-label={`Remove option ${index + 1}`}
                          >
                            <Trash2 className="size-4 text-red-600" />
                          </Button>
                        )}
                      </div>
                    ))}
                  </RadioGroup>
                ) : (
                  <div className="space-y-3">
                    {fields.map((field, index) => (
                      <div
                        key={field.id}
                        className="flex items-start gap-3 rounded-lg border p-4"
                      >
                        <FormField
                          control={form.control}
                          name={`options.${index}.is_correct`}
                          render={({ field }) => (
                            <FormItem className="flex items-center space-y-0">
                              <FormControl>
                                <Checkbox
                                  checked={field.value}
                                  onCheckedChange={(checked) => {
                                    form.setValue(
                                      `options.${index}.is_correct`,
                                      checked === true,
                                      { shouldValidate: true, shouldDirty: true },
                                    );
                                  }}
                                  className="mt-2"
                                  aria-label={`Mark option ${index + 1} correct`}
                                />
                              </FormControl>
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name={`options.${index}.text`}
                          render={({ field }) => (
                            <FormItem className="flex-1">
                              <FormControl>
                                <Input
                                  placeholder={`Option ${index + 1}`}
                                  {...field}
                                />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        {fields.length > 2 && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            onClick={() => removeOption(index)}
                            aria-label={`Remove option ${index + 1}`}
                          >
                            <Trash2 className="size-4 text-red-600" />
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                <div className="flex flex-wrap items-center gap-3">
                  {fields.length < 10 && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => append({ text: "", is_correct: false })}
                    >
                      <Plus className="mr-2 size-4" />
                      Add Option
                    </Button>
                  )}
                  <p className="text-xs text-slate-500">
                    {selectedType === "mcq"
                      ? "Use the radio control to choose exactly one correct option."
                      : "Use checkboxes to mark each correct option."}
                  </p>
                </div>

                {optionsErrorMessage && (
                  <p className="text-sm font-medium text-destructive">
                    {optionsErrorMessage}
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {selectedType === "true_false" && (
            <Card>
              <CardHeader>
                <CardTitle>Correct Answer</CardTitle>
                <CardDescription>
                  Select whether the correct answer is true or false
                </CardDescription>
              </CardHeader>
              <CardContent>
                <FormField
                  control={form.control}
                  name="true_false_answer"
                  render={({ field }) => (
                    <FormItem className="space-y-3">
                      <FormControl>
                        <RadioGroup
                          onValueChange={(value) => field.onChange(value === "true")}
                          value={
                            field.value === true
                              ? "true"
                              : field.value === false
                                ? "false"
                                : undefined
                          }
                          className="flex flex-col space-y-2"
                        >
                          <FormItem className="flex items-center space-x-3 space-y-0 rounded-lg border p-4 hover:bg-green-50">
                            <FormControl>
                              <RadioGroupItem value="true" />
                            </FormControl>
                            <FormLabel className="cursor-pointer font-normal">
                              True
                            </FormLabel>
                          </FormItem>
                          <FormItem className="flex items-center space-x-3 space-y-0 rounded-lg border p-4 hover:bg-red-50">
                            <FormControl>
                              <RadioGroupItem value="false" />
                            </FormControl>
                            <FormLabel className="cursor-pointer font-normal">
                              False
                            </FormLabel>
                          </FormItem>
                        </RadioGroup>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </CardContent>
            </Card>
          )}

          {selectedType === "text" && (
            <Card>
              <CardHeader>
                <CardTitle>Sample Answer</CardTitle>
                <CardDescription>
                  Provide an example of a good answer
                </CardDescription>
              </CardHeader>
              <CardContent>
                <FormField
                  control={form.control}
                  name="sample_answer"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <Textarea
                          placeholder="Enter a sample answer..."
                          className="min-h-[100px]"
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        Minimum 10 characters required
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Answer Explanation</CardTitle>
              <CardDescription>
                Explain why the answer is correct
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="answer_explanation"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Textarea
                        placeholder="Explain the correct answer..."
                        className="min-h-[100px]"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>Optional</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Difficulty Level</CardTitle>
              <CardDescription>
                Rate the difficulty of this question
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="difficulty"
                render={({ field }) => (
                  <FormItem>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select difficulty" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="easy">Easy</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="hard">Hard</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Skills</CardTitle>
              <CardDescription>
                Select skills that this question assesses
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="skills"
                render={({ field }) => {
                  const current = Array.isArray(field.value) ? field.value : [];

                  return (
                    <FormItem>
                      <div className="space-y-4">
                        <Input
                          placeholder="Search skills..."
                          value={searchQuery}
                          onChange={(event) => setSearchQuery(event.target.value)}
                          className="max-w-md"
                        />

                        {selectedSkills.length > 0 && (
                          <div className="flex flex-wrap gap-2">
                            {selectedSkills.map((skill) => (
                              <Badge
                                key={skill}
                                variant="secondary"
                                className="flex items-center gap-2 rounded-full px-3 py-1 text-xs"
                              >
                                <span>{skill}</span>
                                <button
                                  type="button"
                                  onClick={() => {
                                    const updated = current.filter(
                                      (value) => value !== skill,
                                    );
                                    field.onChange(updated);
                                  }}
                                  className="rounded-full p-1 text-orange-500 transition hover:bg-white/60 hover:text-orange-600"
                                  aria-label={`Remove ${skill}`}
                                >
                                  <X className="size-3" />
                                </button>
                              </Badge>
                            ))}
                          </div>
                        )}

                        {loadingSkills ? (
                          <div className="flex h-48 items-center justify-center rounded-lg border border-dashed bg-slate-50">
                            <div className="text-center">
                              <div className="mx-auto h-8 w-8 animate-spin rounded-full border-b-2 border-slate-900" />
                              <p className="mt-2 text-sm text-slate-600">
                                Loading skills...
                              </p>
                            </div>
                          </div>
                        ) : skillsError ? (
                          <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center text-sm text-red-600">
                            {skillsError}
                          </div>
                        ) : filteredSkills.length === 0 ? (
                          <div className="rounded-lg border border-dashed bg-white p-6 text-center text-sm text-slate-500">
                            No skills match your search.
                          </div>
                        ) : (
                          <div className={skillListContainerClass}>
                            <div className="grid gap-2 p-4 sm:grid-cols-2 lg:grid-cols-3">
                              {filteredSkills.map((skill) => {
                                const isChecked = current.includes(skill.name);

                                return (
                                  <div
                                    key={skill.id}
                                    className="flex flex-row items-start space-x-3 rounded-md border p-3 hover:bg-muted/50"
                                  >
                                    <Checkbox
                                      checked={isChecked}
                                      onCheckedChange={(checked) => {
                                        const updated =
                                          checked === true
                                            ? Array.from(new Set([...current, skill.name]))
                                            : current.filter(
                                                (value) => value !== skill.name,
                                              );
                                        field.onChange(updated);
                                      }}
                                    />
                                    <label className="cursor-pointer text-sm font-normal">
                                      {skill.name}
                                      {skill.description && (
                                        <span className="ml-2 text-xs text-slate-500">
                                          ({skill.description})
                                        </span>
                                      )}
                                    </label>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                      <FormMessage />
                    </FormItem>
                  );
                }}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Tags</CardTitle>
              <CardDescription>
                Add tags separated by commas
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="tags"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Input
                        placeholder="e.g., loops, arrays, basics"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>Optional, maximum 30 tags</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <div className="flex justify-end gap-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => router.back()}
              disabled={form.formState.isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={form.formState.isSubmitting}
              className="bg-orange-500 hover:bg-orange-600"
            >
              {form.formState.isSubmitting ? (
                <>
                  <div className="mr-2 h-4 w-4 animate-spin rounded-full border-b-2 border-white" />
                  Creating...
                </>
              ) : (
                <>
                  <Check className="mr-2 size-4" />
                  Create Question
                </>
              )}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
