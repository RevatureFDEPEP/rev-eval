"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, BookOpen, CheckCircle2, Edit, Tag, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Question, QuestionType, deleteQuestion } from "@/lib/api";
import { toast } from "sonner";
import { formatRelativeTime } from "@/lib/utils/date";

interface QuestionDetailsSheetProps {
  question: Question;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDelete?: () => void;
}

export function QuestionDetailsSheet({
  question,
  open,
  onOpenChange,
  onDelete,
}: QuestionDetailsSheetProps) {
  const router = useRouter();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const getTypeColor = (type: QuestionType) => {
    switch (type) {
      case "mcq":
        return "bg-blue-100 text-blue-700";
      case "multi":
        return "bg-purple-100 text-purple-700";
      case "true_false":
        return "bg-green-100 text-green-700";
      case "text":
        return "bg-orange-100 text-orange-700";
    }
  };

  const getTypeLabel = (type: QuestionType) => {
    switch (type) {
      case "mcq":
        return "Single Choice";
      case "multi":
        return "Multiple Choice";
      case "true_false":
        return "True/False";
      case "text":
        return "Text Answer";
    }
  };

  const getDifficultyColor = (difficulty?: string) => {
    switch (difficulty) {
      case "easy":
        return "bg-green-100 text-green-700";
      case "medium":
        return "bg-yellow-100 text-yellow-700";
      case "hard":
        return "bg-red-100 text-red-700";
      default:
        return "bg-slate-100 text-slate-700";
    }
  };

  const handleDelete = async () => {
    if (!question.id) return;

    try {
      setDeleting(true);
      await deleteQuestion(question.id);
      toast.success("Question deleted", {
        description: "The question has been removed from your question bank.",
      });
      setDeleteDialogOpen(false);
      onOpenChange(false);
      onDelete?.();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "An error occurred. Please try again.";
      toast.error("Failed to delete question", {
        description: message,
      });
    } finally {
      setDeleting(false);
    }
  };

  const isCorrectAnswer = (optionId: number): boolean => {
    if (!question.correct_answers) return false;
    return question.correct_answers.includes(optionId);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full overflow-y-auto bg-white/95 sm:max-w-[90vw] lg:max-w-[70vw]"
      >
        <SheetTitle className="sr-only">Question Details</SheetTitle>
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 pb-16">
          <header className="space-y-4 pt-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className={`rounded-full px-3 py-1 text-xs ${getTypeColor(question.type)}`}>
                {getTypeLabel(question.type)}
              </Badge>
              {question.difficulty && (
                <Badge className={`rounded-full px-3 py-1 text-xs ${getDifficultyColor(question.difficulty)}`}>
                  {question.difficulty}
                </Badge>
              )}
              {question.tags && question.tags.length > 0 && (
                <div className="flex flex-wrap items-center gap-1">
                  {question.tags.map((tag) => (
                    <Badge key={tag} variant="outline" className="rounded-full px-2.5 py-1 text-[11px]">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
            <div className="flex flex-wrap items-start justify-between gap-4 rounded-2xl border border-slate-200/70 bg-white/90 p-4 shadow-sm">
              <div className="max-w-3xl space-y-2">
                <h2 className="line-clamp-3 text-2xl font-semibold leading-snug text-slate-900">
                  {question.question_text}
                </h2>
                <p className="text-xs text-slate-500">
                  Created {formatRelativeTime(question.created_at)} · Updated{' '}
                  {formatRelativeTime(question.updated_at)}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  variant="outline"
                  onClick={() => router.push(`/trainer/questions/edit/${question.id}`)}
                >
                  <Edit className="mr-2 size-4" />
                  Edit Question
                </Button>
                <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                  <AlertDialogTrigger asChild>
                    <Button variant="destructive" size="sm">
                      <Trash2 className="mr-2 size-4" />
                      Delete
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Delete Question?</AlertDialogTitle>
                      <AlertDialogDescription>
                        This action cannot be undone. The question will be permanently removed from your question bank.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={handleDelete}
                        disabled={deleting}
                        className="bg-red-600 hover:bg-red-700"
                      >
                        {deleting ? 'Deleting...' : 'Delete'}
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            </div>
          </header>

          <Tabs defaultValue="overview" className="space-y-6">
            <TabsList className="grid w-full grid-cols-3 gap-2 rounded-full bg-muted/70 p-1 text-sm">
              <TabsTrigger
                value="overview"
                className="rounded-full px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-white/70 data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm"
              >
                Overview
              </TabsTrigger>
              <TabsTrigger
                value="usage"
                className="rounded-full px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-white/70 data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm"
              >
                Usage
              </TabsTrigger>
              <TabsTrigger
                value="edit"
                className="rounded-full px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-white/70 data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm"
              >
                Edit
              </TabsTrigger>
            </TabsList>

            {/* Overview Tab */}
            <TabsContent value="overview" className="space-y-4">
              {/* Question Text */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BookOpen className="size-5 text-orange-400" />
                    Question
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="whitespace-pre-wrap text-slate-900">
                    {question.question_text}
                  </p>
                </CardContent>
              </Card>

              {/* Options (for MCQ/Multi) */}
              {(question.type === "mcq" || question.type === "multi") &&
                question.options && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        Answer Options
                      </CardTitle>
                      <CardDescription>
                        {question.type === "mcq"
                          ? "One correct answer"
                          : "Multiple correct answers possible"}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {question.options.map((option) => (
                          <div
                            key={option.option_id}
                            className={`flex items-start gap-3 rounded-lg border p-3 ${
                              isCorrectAnswer(option.option_id)
                                ? "border-green-200 bg-green-50"
                                : "border-slate-200 bg-slate-50"
                            }`}
                          >
                            {isCorrectAnswer(option.option_id) ? (
                              <CheckCircle2 className="mt-0.5 size-5 flex-shrink-0 text-green-600" />
                            ) : (
                              <div className="mt-0.5 size-5 flex-shrink-0 rounded-full border-2 border-slate-300" />
                            )}
                            <div className="flex-1">
                              <p className="text-sm font-medium text-slate-900">
                                Option {option.option_id}
                              </p>
                              <p className="mt-1 text-sm text-slate-700">
                                {option.text}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

              {/* Sample Answer (for text questions) */}
              {question.sample_answer && (
                <Card>
                  <CardHeader>
                    <CardTitle>Sample Answer</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="whitespace-pre-wrap text-sm text-slate-700">
                      {question.sample_answer}
                    </p>
                  </CardContent>
                </Card>
              )}

              {/* Answer Explanation */}
              {question.answer_explanation && (
                <Card>
                  <CardHeader>
                    <CardTitle>Answer Explanation</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="whitespace-pre-wrap text-sm text-slate-700">
                      {question.answer_explanation}
                    </p>
                  </CardContent>
                </Card>
              )}

              {/* Skills */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Tag className="size-4 text-slate-500" />
                    Skills
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {question.skills.map((skill) => (
                      <Badge
                        key={skill}
                        variant="secondary"
                        className="bg-orange-100 text-orange-700"
                      >
                        {skill}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Tags */}
              {question.tags.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Tags</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {question.tags.map((tag) => (
                        <Badge
                          key={tag}
                          variant="outline"
                          className="text-slate-600"
                        >
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Metadata */}
              <Card>
                <CardHeader>
                  <CardTitle>Metadata</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Created:</span>
                    <span className="font-medium text-slate-900">
                      {formatRelativeTime(question.created_at)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Last Updated:</span>
                    <span className="font-medium text-slate-900">
                      {formatRelativeTime(question.updated_at)}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Usage Tab */}
            <TabsContent value="usage">
              <Card>
                <CardHeader>
                  <CardTitle>Question Usage</CardTitle>
                  <CardDescription>
                    See which tests use this question
                  </CardDescription>
                </CardHeader>
                <CardContent className="py-12 text-center">
                  <div className="rounded-full bg-slate-100 p-3 inline-block">
                    <AlertCircle className="size-6 text-slate-400" />
                  </div>
                  <p className="mt-4 text-sm text-slate-600">
                    Usage tracking coming soon
                  </p>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Edit Tab */}
            <TabsContent value="edit">
              <Card>
                <CardHeader>
                  <CardTitle>Edit Question</CardTitle>
                  <CardDescription>
                    Modify question details and settings
                  </CardDescription>
                </CardHeader>
                <CardContent className="py-12 text-center">
                  <div className="rounded-full bg-slate-100 p-3 inline-block">
                    <Edit className="size-6 text-slate-400" />
                  </div>
                  <p className="mt-4 text-sm text-slate-600">
                    Edit functionality coming soon
                  </p>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </SheetContent>
    </Sheet>
  );
}
