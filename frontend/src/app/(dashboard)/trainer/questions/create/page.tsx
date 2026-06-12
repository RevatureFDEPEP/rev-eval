"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
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
  createQuestion,
  QuestionCreate,
  QuestionType,
  getSkills,
  SkillInfo,
} from "@/lib/api";
import { ApiError } from "@/lib/api/client";
import { api } from "@/lib/api/client";
import { toast } from "sonner";

// ---------------------------------------------------------------------------
// Single flat form type — all type-specific fields optional.
// Using a discriminated union here causes TypeScript to reject field accesses
// (options, true_false_answer, sample_answer) that don't exist on every
// union member, and breaks useFieldArray which requires options to be a
// non-optional array.
// ---------------------------------------------------------------------------
interface QuestionFormValues {
  question_text: string;
  difficulty?: "easy" | "medium" | "hard";
  skills: string[];
  tags?: string; // raw comma-separated string; split in transformFormData
  answer_explanation?: string;
  // Always-present array so useFieldArray is satisfied; non-MCQ forms leave it empty.
  options: Array<{ text: string; is_correct: boolean }>;
  // Type-specific optional fields
  true_false_answer?: boolean;
  sample_answer?: string;
}

// ---------------------------------------------------------------------------
// Zod schemas — used for runtime validation only, not for type inference.
// ---------------------------------------------------------------------------

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

export default function CreateQuestionPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [loadingSkills, setLoadingSkills] = useState(true);

  const questionType = (searchParams.get("type") as QuestionType) || "mcq";

  const getSchema = () => {
    switch (questionType) {
      case "true_false":
        return trueFalseSchema;
      case "text":
        return textSchema;
      default:
        return mcqSchema;
    }
  };

  const getDefaultValues = (): QuestionFormValues => {
    const base: QuestionFormValues = {
      question_text: "",
      difficulty: undefined,
      skills: [],
      tags: "",
      answer_explanation: "",
      options: [],
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
        return { ...base, true_false_answer: undefined };
      case "text":
        return { ...base, sample_answer: "" };
      default:
        return base;
    }
  };

  const form = useForm<QuestionFormValues>({
    // Cast required: Zod schema output types differ from the flat interface.
    // Runtime validation is still correct — only the static type is widened.
    resolver: zodResolver(getSchema()) as Resolver<QuestionFormValues>,
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
    if (!searchQuery.trim()) return skills;
    const query = searchQuery.toLowerCase();
    return skills.filter((skill) => skill.name.toLowerCase().includes(query));
  }, [skills, searchQuery]);

  const skillListContainerClass =
    "max-h-[55vh] overflow-x-hidden overflow-y-auto overscroll-contain rounded-lg border border-slate-200 bg-white";

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

  const transformFormData = (values: QuestionFormValues): QuestionCreate => {
    let actualType: QuestionType = questionType;
    let correct_answers: (number | boolean | string)[] | undefined = undefined;
    let options: { text: string }[] | undefined = undefined;

    if (questionType === "mcq") {
      const correctIndices = values.options
        .map((opt, idx) => (opt.is_correct ? idx + 1 : null))
        .filter((id): id is number => id !== null);

      actualType = correctIndices.length > 1 ? "multi" : "mcq";
      correct_answers = correctIndices;
      options = values.options.map((opt) => ({ text: opt.text }));
    } else if (questionType === "true_false") {
      correct_answers =
        values.true_false_answer !== undefined ? [values.true_false_answer] : [];
    }
    // text: correct_answers and options stay undefined

    return {
      type: actualType,
      question_text: values.question_text,
      difficulty: values.difficulty,
      skills: values.skills,
      tags: values.tags
        ? values.tags.split(",").map((t) => t.trim()).filter(Boolean)
        : [],
      options,
      correct_answers,
      sample_answer: values.sample_answer || undefined,
      answer_explanation: values.answer_explanation || undefined,
    };
  };

  const uploadImageToMinIO = async (questionId: string, file: File): Promise<void> => {
    setUploadingImage(true);
    try {
      const { url } = await api.post<{ url: string; key: string; expires_in: number }>(
        `/v1/api/questions/${questionId}/image/upload-url?content_type=${encodeURIComponent(file.type)}`
      );
      await fetch(url, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": file.type },
      });
    } finally {
      setUploadingImage(false);
    }
  };

  const mapValidationErrors = (err: unknown): boolean => {
    if (!(err instanceof ApiError) || err.status !== 422) return false;
    try {
      const body = JSON.parse(err.body as string) as {
        detail?: Array<{ loc: string[]; msg: string }>;
      };
      if (!Array.isArray(body?.detail)) return false;
      for (const e of body.detail) {
        // loc is ["body", "field_name"] — drop the "body" prefix
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
      const data = transformFormData(values);
      const question = await createQuestion(data);
      if (imageFile && question.id) {
        await uploadImageToMinIO(question.id, imageFile);
      }
      toast.success("Question created successfully!", {
        description: `"${values.question_text.slice(0, 50)}..." has been added to your question bank.`,
      });
      router.push("/trainer/questions");
    } catch (err) {
      console.error("Failed to create question:", err);
      if (mapValidationErrors(err)) return; // RHF setError handles display
      const errorMessage =
        err instanceof Error ? err.message : "Failed to create question";
      setError(errorMessage);
      toast.error("Failed to create question", { description: errorMessage });
    } finally {
      setSubmitting(false);
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case "mcq":        return "MCQ";
      case "true_false": return "True/False";
      case "text":       return "Text Answer";
      default:           return type;
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
          <p className="text-sm text-slate-500">{getTypeLabel(questionType)} question</p>
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
              <CardDescription>Enter the question that students will see</CardDescription>
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
                    <FormDescription>Minimum 10 characters required</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Options (MCQ only) */}
          {questionType === "mcq" && (
            <Card>
              <CardHeader>
                <CardTitle>Answer Options</CardTitle>
                <CardDescription>
                  Add 2-5 options and check the correct answer(s). You can select one or
                  multiple correct answers.
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
                            <Input placeholder={`Option ${index + 1}`} {...field} />
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
                            <FormLabel className="cursor-pointer font-normal">True</FormLabel>
                          </FormItem>
                          <FormItem className="flex items-center space-x-3 space-y-0 rounded-lg border p-4 hover:bg-red-50">
                            <FormControl>
                              <RadioGroupItem value="false" />
                            </FormControl>
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

          {/* Sample Answer (Text questions only) */}
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
                          value={field.value ?? ""}
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
              <CardDescription>Explain why the answer is correct</CardDescription>
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
                        value={field.value ?? ""}
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
              <CardDescription>Rate the difficulty of this question</CardDescription>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="difficulty"
                render={({ field }) => (
                  <FormItem>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
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
                                  const updated = selectedSkills.filter(
                                    (value: string) => value !== skill
                                  );
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
                                              ? Array.from(
                                                  new Set([...current, skill.name])
                                                )
                                              : current.filter(
                                                  (value) => value !== skill.name
                                                );
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
              <CardDescription>Add tags separated by commas (max 30)</CardDescription>
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
                        value={field.value ?? ""}
                      />
                    </FormControl>
                    <FormDescription>Separate tags with commas</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Image Upload (optional) */}
          <Card>
            <CardHeader>
              <CardTitle>Question Image (Optional)</CardTitle>
              <CardDescription>
                Attach a diagram or image. Uploaded directly to object storage via presigned URL.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Input
                type="file"
                accept="image/*"
                onChange={(e) => setImageFile(e.target.files?.[0] ?? null)}
                className="cursor-pointer"
              />
              {imageFile && (
                <p className="mt-2 text-xs text-slate-500">
                  Selected: {imageFile.name} ({(imageFile.size / 1024).toFixed(1)} KB)
                </p>
              )}
              {uploadingImage && (
                <p className="mt-2 text-xs text-orange-500">Uploading image...</p>
              )}
            </CardContent>
          </Card>

          {/* Submit */}
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
