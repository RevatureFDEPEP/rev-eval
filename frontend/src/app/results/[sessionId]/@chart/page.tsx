/**
 * Score chart region (@chart slot) — async server component.
 *
 * Fetches the attempt history server-side (up to 100 attempts so the trend
 * covers the full history, not just the table's first page) and hands it to
 * the <ScoreTrendChart> client component as the initial prop — the chart
 * hydrates from server data with no client fetch.
 */
import { redirect } from 'next/navigation';
import { getSession } from '@/lib/session';
import { getUserReportAttemptsServer } from '@/lib/api/server';
import { Card, CardContent } from '@/components/ui/card';
import { ScoreTrendChart } from '@/components/charts/ScoreTrendChart';

interface ChartPageProps {
  params: Promise<{ sessionId: string }>;
}

export default async function ChartPage({ params }: ChartPageProps) {
  const { sessionId } = await params;

  const session = await getSession();
  if (!session) {
    redirect('/');
  }

  const attempts = await getUserReportAttemptsServer(session.userId, { page: 1, size: 100 });

  return (
    <Card>
      <CardContent className="pt-6">
        <ScoreTrendChart attempts={attempts.items} highlightSessionId={sessionId} />
      </CardContent>
    </Card>
  );
}
