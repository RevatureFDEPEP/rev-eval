import { QuestionAuthorForm } from "@/components/trainer/QuestionAuthorForm";
import type { QuestionType } from "@/lib/api";

type CreateQuestionPageProps = {
  searchParams?:
    | Promise<Record<string, string | string[] | undefined>>
    | Record<string, string | string[] | undefined>;
};

const QUESTION_TYPES = ["mcq", "multi", "true_false", "text"] as const;

function isQuestionType(value: string | undefined): value is QuestionType {
  return QUESTION_TYPES.includes(value as QuestionType);
}

export default async function CreateQuestionPage({
  searchParams,
}: CreateQuestionPageProps) {
  const resolvedSearchParams = await Promise.resolve(searchParams);
  const rawType = resolvedSearchParams?.type;
  const typeParam = Array.isArray(rawType) ? rawType[0] : rawType;
  const initialType = isQuestionType(typeParam) ? typeParam : "mcq";

  return <QuestionAuthorForm initialType={initialType} />;
}
