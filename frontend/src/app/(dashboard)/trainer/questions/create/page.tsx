"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { ArrowLeft, Check, Plus, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  createQuestion,
  QuestionCreate,
  QuestionType,
  getSkills,
  SkillInfo,
} from "@/lib/api";
import { toast } from "sonner";

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

// MCQ-specific schema
const mcqSchema = z
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

// True/False schema
const trueFalseSchema = z.object({
  ...baseSchema,
  true_false_answer: z.boolean(),
});

// Text schema
const textSchema = z.object({
  ...baseSchema,
  sample_answer: z
    .string()
    .min(10, "Sample answer must be at least 10 characters"),
});

type McqFormValues = z.infer<typeof mcqSchema>;
type TrueFalseFormValues = z.infer<typeof trueFalseSchema>;
type TextFormValues = z.infer<typeof textSchema>;
type QuestionFormValues = McqFormValues | TrueFalseFormValues | TextFormValues;

export default function CreateQuestionPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [loadingSkills, setLoadingSkills] = useState(true);

  const questionType = (searchParams.get("type") as QuestionType) || "mcq";

  // Select the appropriate schema based on question type
  const getSchema = () => {
    switch (questionType) {
      case "mcq":
        return mcqSchema;
      case "true_false":
        return trueFalseSchema;
      case "text":
        return textSchema;
      default:
        return mcqSchema;
    }
  };

  // Get default values based on question type
  const getDefaultValues = (): any => {
    const base = {
      question_text: "",
      difficulty: undefined,
      skills: [],
      tags: "",
      answer_explanation: "",
    };

    switch (questionType) {
      case "mcq":
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
  };

  const form = useForm<any>({
    resolver: zodResolver(getSchema()),
    defaultValues: getDefaultValues(),
  });

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "options",
  });

  const watchSkills = form.watch("skills");
  const selectedSkills = Array.isArray(watchSkills) ? watchSkills : [];
  const [searchQuery, setSearchQuery] = useState("");
  const filteredSkills = useMemo(() => {
    if (!searchQuery.trim()) {
      return skills;
    }
    const query = searchQuery.toLowerCase();
    return skills.filter((skill) => skill.name.toLowerCase().includes(query));
  }, [skills, searchQuery]);
  const skillListContainerClass =
    'max-h-[55vh] overflow-x-hidden overflow-y-auto overscroll-contain rounded-lg border border-slate-200 bg-white';

  // Load skills
  useEffect(() => {
    const loadSkills = async () => {
      try {
        const data = await getSkills();
        setSkills(data);
      } catch (err) {
        console.error("Failed to load skills:", err);
      } finally {
        setLoadingSkills(false);
      }
    };
    loadSkills();
  }, []);

  const transformFormData = (values: any): QuestionCreate => {
    // For MCQ type, determine if it's actually MCQ (single answer) or MULTI (multiple answers)
    let actualType: QuestionType = questionType;
    let correct_answers: (number | boolean | string)[] | undefined = undefined;
    let options: { text: string }[] | undefined = undefined;

    if (questionType === "mcq") {
      // Get all correct answers
      const correctAnswerIndices = values.options
        .map((opt: any, idx: number) => (opt.is_correct ? idx + 1 : null))
        .filter((id: any): id is number => id !== null);

      // Determine if it's MCQ (1 answer) or MULTI (2+ answers)
      if (correctAnswerIndices.length === 1) {
        actualType = "mcq";
      } else if (correctAnswerIndices.length > 1) {
        actualType = "multi";
      }

      correct_answers = correctAnswerIndices;
      options = values.options.map((opt: any) => ({ text: opt.text }));
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
  };

  const onSubmit = async (values: QuestionFormValues) => {
    try {
      setSubmitting(true);
      setError(null);
      const data = transformFormData(values);
      await createQuestion(data);
      toast.success("Question created successfully!", {
        description: `"${values.question_text.slice(0, 50)}..." has been added to your question bank.`,
      });
      router.push("/trainer/questions");
    } catch (err: any) {
      console.error("Failed to create question:", err);
      const errorMessage = err.message || "Failed to create question";
      setError(errorMessage);
      toast.error("Failed to create question", {
        description: errorMessage,
      });
    } finally {
      setSubmitting(false);
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case "mcq":
        return "MCQ";
      case "true_false":
        return "True/False";
      case "text":
        return "Text Answer";
      default:
        return type;
    }
  };

  return (
    <div className="container mx-auto max-w-4xl space-y-8 px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.back()}
          className="shrink-0"
        >
          <ArrowLeft className="size-4" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            Create New Question
          </h1>
          <p className="text-sm text-slate-500">
            {getTypeLabel(questionType)} question
          </p>
        </div>
      </div>

      {error && (
        <Card className="border-red-200 bg-red-50/50">
          <CardContent className="py-4">
            <p className="text-sm text-red-600">{error}</p>
          </CardContent>
        </Card>
      )}

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* Question Text */}
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

          {/* Options (for MCQ) */}
          {questionType === "mcq" && (
            <Card>
              <CardHeader>
                <CardTitle>Answer Options</CardTitle>
                <CardDescription>
                  Add 2-5 options and check the correct answer(s). You can select one or multiple correct answers.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
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
                              onCheckedChange={field.onChange}
                              className="mt-1"
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
                        onClick={() => remove(index)}
                      >
                        <Trash2 className="size-4 text-red-600" />
                      </Button>
                    )}
                  </div>
                ))}
                {fields.length < 5 && (
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
                {form.formState.errors.options?.message && (
                  <p className="text-sm font-medium text-destructive">
                    {String(form.formState.errors.options.message)}
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {/* True/False Answer Selection */}
          {questionType === "true_false" && (
            <Card>
              <CardHeader>
                <CardTitle>Correct Answer</CardTitle>
                <CardDescription>
                  Select whether the correct answer is True or False
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
                          value={field.value === true ? "true" : field.value === false ? "false" : undefined}
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

          {/* Sample Answer (for Text questions) */}
          {questionType === "text" && (
            <Card>
              <CardHeader>
                <CardTitle>Sample Answer *</CardTitle>
                <CardDescription>
                  Provide an example of a good answer (minimum 10 characters)
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
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </CardContent>
            </Card>
          )}

          {/* Answer Explanation */}
          <Card>
            <CardHeader>
              <CardTitle>Answer Explanation (Optional)</CardTitle>
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
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Difficulty */}
          <Card>
            <CardHeader>
              <CardTitle>Difficulty Level (Optional)</CardTitle>
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
                    <Select
                      onValueChange={field.onChange}
                      defaultValue={field.value}
                    >
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

          {/* Skills */}
          <Card>
            <CardHeader>
              <CardTitle>Skills *</CardTitle>
              <CardDescription>
                Select skills that this question assesses (1-20)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="skills"
                render={() => (
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
                          {selectedSkills.map((skill: string) => (
                            <Badge
                              key={skill}
                              variant="secondary"
                              className="flex items-center gap-2 rounded-full px-3 py-1 text-xs"
                            >
                              <span>{skill}</span>
                              <button
                                type="button"
                                onClick={() => {
                                  const updated = selectedSkills.filter((value: string) => value !== skill);
                                  form.setValue("skills", updated, {
                                    shouldValidate: true,
                                    shouldDirty: true,
                                  });
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
                            <p className="mt-2 text-sm text-slate-600">Loading skills...</p>
                          </div>
                        </div>
                      ) : filteredSkills.length === 0 ? (
                        <div className="rounded-lg border border-dashed bg-white p-6 text-center text-sm text-slate-500">
                          No skills match your search.
                        </div>
                      ) : (
                        <div className={skillListContainerClass}>
                          <div className="grid gap-2 p-4 sm:grid-cols-2 lg:grid-cols-3">
                            {filteredSkills.map((skill) => (
                              <FormField
                                key={skill.id}
                                control={form.control}
                                name="skills"
                                render={({ field }) => {
                                  const current: string[] = field.value || [];
                                  const isChecked = current.includes(skill.name);
                                  return (
                                    <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-3 hover:bg-muted/50">
                                      <FormControl>
                                        <Checkbox
                                          checked={isChecked}
                                          onCheckedChange={(checked) => {
                                            const updated = checked
                                              ? Array.from(new Set([...current, skill.name]))
                                              : current.filter((value) => value !== skill.name);
                                            field.onChange(updated);
                                          }}
                                        />
                                      </FormControl>
                                      <FormLabel className="cursor-pointer text-sm font-normal">
                                        {skill.name}
                                        {skill.description && (
                                          <span className="ml-2 text-xs text-slate-500">
                                            ({skill.description})
                                          </span>
                                        )}
                                      </FormLabel>
                                    </FormItem>
                                  );
                                }}
                              />
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Tags */}
          <Card>
            <CardHeader>
              <CardTitle>Tags (Optional)</CardTitle>
              <CardDescription>
                Add tags separated by commas (max 30)
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
                        value={
                          typeof field.value === "string"
                            ? field.value
                            : field.value?.join(", ") || ""
                        }
                      />
                    </FormControl>
                    <FormDescription>
                      Separate tags with commas
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Submit Button */}
          <div className="flex justify-end gap-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => router.back()}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={submitting}
              className="bg-orange-500 hover:bg-orange-600"
            >
              {submitting ? (
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
