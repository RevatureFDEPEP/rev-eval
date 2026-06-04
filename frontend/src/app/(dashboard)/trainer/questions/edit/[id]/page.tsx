"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  ApiError,
  getQuestion,
  updateQuestion,
  QuestionCreate,
  QuestionType,
} from "@/lib/api";
import { QuestionForm } from "@/components/trainer/QuestionForm";
import {
  QuestionFormInitial,
  toInitial,
} from "@/components/trainer/question-form-utils";
import { toast } from "sonner";

export default function EditQuestionPage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [questionType, setQuestionType] = useState<QuestionType | null>(null);
  const [initialData, setInitialData] = useState<QuestionFormInitial | null>(
    null
  );

  // Load the question and map it to form initial values
  useEffect(() => {
    const loadQuestion = async () => {
      try {
        const question = await getQuestion(id);
        const { type, data } = toInitial(question);
        setQuestionType(type);
        setInitialData(data);
      } catch (err) {
        console.error("Failed to load question:", err);
        if (err instanceof ApiError && err.status === 404) {
          setNotFound(true);
        } else {
          setError(
            err instanceof Error ? err.message : "Failed to load question"
          );
        }
      } finally {
        setLoading(false);
      }
    };
    loadQuestion();
  }, [id]);

  const onSubmit = async (data: QuestionCreate) => {
    try {
      setSubmitting(true);
      setError(null);
      await updateQuestion(id, data);
      toast.success("Question updated successfully!", {
        description: `"${data.question_text.slice(0, 50)}..." has been saved.`,
      });
      router.push("/trainer/questions");
    } catch (err) {
      console.error("Failed to update question:", err);
      const errorMessage =
        err instanceof Error ? err.message : "Failed to update question";
      setError(errorMessage);
      toast.error("Failed to update question", {
        description: errorMessage,
      });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto flex max-w-4xl items-center justify-center px-4 py-24">
        <div className="text-center">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-b-2 border-slate-900" />
          <p className="mt-2 text-sm text-slate-600">Loading question...</p>
        </div>
      </div>
    );
  }

  if (notFound || !initialData || !questionType) {
    return (
      <div className="container mx-auto max-w-4xl space-y-6 px-4 py-8">
        <Card className="border-red-200 bg-red-50/50">
          <CardContent className="space-y-4 py-6">
            <p className="text-sm text-red-600">
              {notFound
                ? "Question not found. It may have been deleted."
                : error || "Failed to load question"}
            </p>
            <Button variant="outline" asChild>
              <Link href="/trainer/questions">
                <ArrowLeft className="mr-2 size-4" />
                Back to Questions
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <QuestionForm
      mode="edit"
      questionType={questionType}
      initialData={initialData}
      onSubmit={onSubmit}
      submitting={submitting}
      error={error}
    />
  );
}
