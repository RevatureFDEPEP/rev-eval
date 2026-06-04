"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createQuestion, QuestionCreate, QuestionType } from "@/lib/api";
import { QuestionForm } from "@/components/trainer/QuestionForm";
import { toast } from "sonner";

export default function CreateQuestionPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const questionType = (searchParams.get("type") as QuestionType) || "mcq";

  const onSubmit = async (data: QuestionCreate) => {
    try {
      setSubmitting(true);
      setError(null);
      await createQuestion(data);
      toast.success("Question created successfully!", {
        description: `"${data.question_text.slice(0, 50)}..." has been added to your question bank.`,
      });
      router.push("/trainer/questions");
    } catch (err) {
      console.error("Failed to create question:", err);
      const errorMessage = err instanceof Error ? err.message : "Failed to create question";
      setError(errorMessage);
      toast.error("Failed to create question", {
        description: errorMessage,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <QuestionForm
      mode="create"
      questionType={questionType}
      onSubmit={onSubmit}
      submitting={submitting}
      error={error}
    />
  );
}
