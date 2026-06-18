"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useForm, useFieldArray, type Resolver } from "react-hook-form";
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
  getQuestion,
  updateQuestion,
  QuestionType,
  getSkills,
  SkillInfo,
} from "@/lib/api";
import { ApiError } from "@/lib/api/client";
import { toast } from "sonner";

interface QuestionFormValues {
  question_text: string;
  difficulty?: "easy" | "medium" | "hard";
  skills: string[];
  tags?: string;
  answer_explanation?: string;
  options: Array<{ text: string; is_correct: boolean }>;
  true_false_answer?: boolean;
  sample_answer?: string;
}

const baseSchema = {
  question_text: z.string().min(10, "Question must be at least 10 characters"),
  difficulty: z.enum(["easy", "medium", "hard"]).optional(),
  skills: z
    .array(z.string())
    .min(1, "Select at least one skill")
    .max(20, "Maximum 20 skills allowed"),
  tags: z.string().optional(),
  answer_explanation: z.string().optional(),
};

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
    (data) =>
      data.options.length >= 2 &&
      data.options.length <= 5 &&
      data.options.some((opt) => opt.is_correct),
    {
      message: "MCQ questions require 2-5 options with at least one marked correct",
      path: ["options"],
    }
  );

const trueFalseSchema = z
  .object({
    ...baseSchema,
    options: z.array(z.object({ text: z.string(), is_correct: z.boolean() })).optional(),
    true_false_answer: z.boolean().optional(),
  })
  .refine((data) => data.true_false_answer !== undefined, {
    message: "Please select True or False",
    path: ["true_false_answer"],
  });

const textSchema = z.object({
  ...baseSchema,
  options: z.array(z.object({ text: z.string(), is_correct: z.boolean() })).optional(),
  sample_answer: z.string().min(10, "Sample answer must be at least 10 characters"),
});

// "multi" uses mcq form (multiple correct checkboxes)
function getFormType(type: QuestionType): "mcq" | "true_false" | "text" {
  if (type === "mcq" || type === "multi") return "mcq";
  if (type === "true_false") return "true_false";
  return "text";
}

export default function EditQuestionPage() {
  const params = useParams();
  const router = useRouter();
  const questionId = params.id as string;

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingQuestion, setLoadingQuestion] = useState(true);
  const [questionType, setQuestionType] = useState<"mcq" | "true_false" | "text">("mcq");
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [loadingSkills, setLoadingSkills] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  const getSchema = () => {
    switch (questionType) {
      case "true_false": return trueFalseSchema;
      case "text":       return textSchema;
      default:           return mcqSchema;
    }
  };

  const form = useForm<QuestionFormValues>({
    resolver: zodResolver(getSchema()) as Resolver<QuestionFormValues>,
    defaultValues: {
      question_text: "",
      difficulty: undefined,
      skills: [],
      tags: "",
      answer_explanation: "",
      options: [{ text: "", is_correct: false }, { text: "", is_correct: false }],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "options",
  });

  const watchSkills = form.watch("skills");
  const selectedSkills = Array.isArray(watchSkills) ? watchSkills : [];

  const filteredSkills = useMemo(() => {
    if (!searchQuery.trim()) return skills;
    const query = searchQuery.toLowerCase();
    return skills.filter((s) => s.name.toLowerCase().includes(query));
  }, [skills, searchQuery]);

  const skillListContainerClass =
    "max-h-[55vh] overflow-x-hidden overflow-y-auto overscroll-contain rounded-lg border border-slate-200 bg-white";

  useEffect(() => {
    getSkills()
      .then(setSkills)
      .catch((err) => console.error("Failed to load skills:", err))
      .finally(() => setLoadingSkills(false));
  }, []);

  useEffect(() => {
    async function load() {
      try {
        const q = await getQuestion(questionId);
        const formType = getFormType(q.type);
        setQuestionType(formType);

        // Build options for MCQ/multi
        let options: Array<{ text: string; is_correct: boolean }> = [
          { text: "", is_correct: false },
          { text: "", is_correct: false },
        ];
        if ((q.type === "mcq" || q.type === "multi") && q.options) {
          const correctSet = new Set(
            (q.correct_answers ?? []).map((v) => Number(v))
          );
          options = q.options.map((opt) => ({
            text: opt.text,
            is_correct: correctSet.has(opt.option_id),
          }));
        }

        // True/false answer
        let true_false_answer: boolean | undefined = undefined;
        if (q.type === "true_false" && q.correct_answers?.length) {
          true_false_answer = Boolean(q.correct_answers[0]);
        }

        form.reset({
          question_text: q.question_text,
          difficulty: q.difficulty as "easy" | "medium" | "hard" | undefined,
          skills: q.skills ?? [],
          tags: (q.tags ?? []).join(", "),
          answer_explanation: q.answer_explanation ?? "",
          options,
          true_false_answer,
          sample_answer: q.sample_answer ?? "",
        });
      } catch (err) {
        console.error("Failed to load question:", err);
        setError("Failed to load question. It may have been deleted.");
      } finally {
        setLoadingQuestion(false);
      }
    }
    load();
  }, [questionId, form]);

  const transformFormData = (values: QuestionFormValues) => {
    let correct_answers: (number | boolean | string)[] | undefined;
    let options: { text: string }[] | undefined;

    if (questionType === "mcq") {
      const correctIndices = values.options
        .map((opt, idx) => (opt.is_correct ? idx + 1 : null))
        .filter((id): id is number => id !== null);
      correct_answers = correctIndices;
      options = values.options.map((opt) => ({ text: opt.text }));
    } else if (questionType === "true_false") {
      correct_answers = values.true_false_answer !== undefined ? [values.true_false_answer] : [];
    }

    return {
      question_text: values.question_text,
      difficulty: values.difficulty,
      skills: values.skills,
      tags: values.tags ? values.tags.split(",").map((t) => t.trim()).filter(Boolean) : [],
      options,
      correct_answers,
      sample_answer: values.sample_answer || undefined,
      answer_explanation: values.answer_explanation || undefined,
    };
  };

  const mapValidationErrors = (err: unknown): boolean => {
    if (!(err instanceof ApiError) || err.status !== 422) return false;
    try {
      const body = JSON.parse(err.body as string) as {
        detail?: Array<{ loc: string[]; msg: string }>;
      };
      if (!Array.isArray(body?.detail)) return false;
      for (const e of body.detail) {
        const field = e.loc.slice(1).join(".") as keyof QuestionFormValues;
        if (field) form.setError(field, { message: e.msg });
      }
      return true;
    } catch {
      return false;
    }
  };

  const onSubmit = async (values: QuestionFormValues) => {
    try {
      setSubmitting(true);
      setError(null);
      await updateQuestion(questionId, transformFormData(values));
      toast.success("Question updated successfully!");
      router.push("/trainer/questions");
    } catch (err) {
      console.error("Failed to update question:", err);
      if (mapValidationErrors(err)) return;
      const message = err instanceof Error ? err.message : "Failed to update question";
      setError(message);
      toast.error("Failed to update question", { description: message });
    } finally {
      setSubmitting(false);
    }
  };

  const typeLabel = { mcq: "MCQ", true_false: "True/False", text: "Text Answer" };

  if (loadingQuestion) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-b-2 border-slate-900" />
          <p className="mt-4 text-sm text-slate-600">Loading question…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-4xl space-y-8 px-4 py-8">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()} className="shrink-0">
          <ArrowLeft className="size-4" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">Edit Question</h1>
          <p className="text-sm text-slate-500">{typeLabel[questionType]} question</p>
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
              <CardDescription>Edit the question that students will see</CardDescription>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="question_text"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Textarea placeholder="Enter your question here..." className="min-h-[120px]" {...field} />
                    </FormControl>
                    <FormDescription>Minimum 10 characters required</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Options (MCQ) */}
          {questionType === "mcq" && (
            <Card>
              <CardHeader>
                <CardTitle>Answer Options</CardTitle>
                <CardDescription>
                  Edit options and check the correct answer(s).
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {fields.map((field, index) => (
                  <div key={field.id} className="flex items-start gap-3 rounded-lg border p-4">
                    <FormField
                      control={form.control}
                      name={`options.${index}.is_correct`}
                      render={({ field }) => (
                        <FormItem className="flex items-center space-y-0">
                          <FormControl>
                            <Checkbox checked={field.value} onCheckedChange={field.onChange} className="mt-1" />
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
                            <Input placeholder={`Option ${index + 1}`} {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    {fields.length > 2 && (
                      <Button type="button" variant="ghost" size="icon" onClick={() => remove(index)}>
                        <Trash2 className="size-4 text-red-600" />
                      </Button>
                    )}
                  </div>
                ))}
                {fields.length < 5 && (
                  <Button type="button" variant="outline" size="sm" onClick={() => append({ text: "", is_correct: false })}>
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

          {/* True/False */}
          {questionType === "true_false" && (
            <Card>
              <CardHeader>
                <CardTitle>Correct Answer</CardTitle>
                <CardDescription>Select whether the correct answer is True or False</CardDescription>
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
                            <FormControl><RadioGroupItem value="true" /></FormControl>
                            <FormLabel className="cursor-pointer font-normal">True</FormLabel>
                          </FormItem>
                          <FormItem className="flex items-center space-x-3 space-y-0 rounded-lg border p-4 hover:bg-red-50">
                            <FormControl><RadioGroupItem value="false" /></FormControl>
                            <FormLabel className="cursor-pointer font-normal">False</FormLabel>
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

          {/* Sample Answer (text) */}
          {questionType === "text" && (
            <Card>
              <CardHeader>
                <CardTitle>Sample Answer *</CardTitle>
                <CardDescription>Provide an example of a good answer (minimum 10 characters)</CardDescription>
              </CardHeader>
              <CardContent>
                <FormField
                  control={form.control}
                  name="sample_answer"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <Textarea placeholder="Enter a sample answer..." className="min-h-[100px]" {...field} value={field.value ?? ""} />
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
              <CardDescription>Explain why the answer is correct</CardDescription>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="answer_explanation"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Textarea placeholder="Explain the correct answer..." className="min-h-[100px]" {...field} value={field.value ?? ""} />
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
              <CardDescription>Rate the difficulty of this question</CardDescription>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="difficulty"
                render={({ field }) => (
                  <FormItem>
                    <Select onValueChange={field.onChange} value={field.value ?? ""}>
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
              <CardDescription>Select skills that this question assesses (1-20)</CardDescription>
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
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="max-w-md"
                      />

                      {selectedSkills.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {selectedSkills.map((skill: string) => (
                            <Badge key={skill} variant="secondary" className="flex items-center gap-2 rounded-full px-3 py-1 text-xs">
                              <span>{skill}</span>
                              <button
                                type="button"
                                onClick={() => {
                                  const updated = selectedSkills.filter((v: string) => v !== skill);
                                  form.setValue("skills", updated, { shouldValidate: true, shouldDirty: true });
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
                                              : current.filter((v) => v !== skill.name);
                                            field.onChange(updated);
                                          }}
                                        />
                                      </FormControl>
                                      <FormLabel className="cursor-pointer text-sm font-normal">
                                        {skill.name}
                                        {skill.description && (
                                          <span className="ml-2 text-xs text-slate-500">({skill.description})</span>
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
              <CardDescription>Add tags separated by commas (max 30)</CardDescription>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="tags"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Input placeholder="e.g., loops, arrays, basics" {...field} value={field.value ?? ""} />
                    </FormControl>
                    <FormDescription>Separate tags with commas</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Submit */}
          <div className="flex justify-end gap-4">
            <Button type="button" variant="outline" onClick={() => router.back()} disabled={submitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting} className="bg-orange-500 hover:bg-orange-600">
              {submitting ? (
                <>
                  <div className="mr-2 h-4 w-4 animate-spin rounded-full border-b-2 border-white" />
                  Saving…
                </>
              ) : (
                <>
                  <Check className="mr-2 size-4" />
                  Save Changes
                </>
              )}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
