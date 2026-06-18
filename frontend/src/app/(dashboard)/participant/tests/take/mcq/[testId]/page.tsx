import { redirect } from 'next/navigation';

type LegacyQuizPageProps = {
  params: Promise<{ testId: string }>;
  searchParams: Promise<{ submission?: string | string[] }>;
};

function firstSearchValue(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function LegacyQuizPage({
  params,
  searchParams,
}: LegacyQuizPageProps) {
  const [{ testId }, query] = await Promise.all([params, searchParams]);
  const submission = firstSearchValue(query.submission);
  const target = submission
    ? `/take/${encodeURIComponent(testId)}?submission=${encodeURIComponent(submission)}`
    : `/take/${encodeURIComponent(testId)}`;

  redirect(target);
}
