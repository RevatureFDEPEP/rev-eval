/**
 * Summary headline region (children slot) — async server component.
 *
 * Fetches the W4-F1 summary envelope (GET /reports/user/{userId}) with the
 * userId from the auth_token cookie JWT, so the headline numbers are in the
 * initial HTML. The [sessionId] route param is a highlight anchor only — both
 * reporting endpoints are user-scoped (see plan decision 3).
 */
import { redirect } from 'next/navigation';
import { getSession } from '@/lib/session';
import { getUserReportSummaryServer } from '@/lib/api/server';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatDateTime } from '@/lib/utils/date';
import { formatDuration, formatScore } from '@/lib/utils/duration';

export default async function ResultsSummaryPage() {
  const session = await getSession();
  if (!session) {
    redirect('/');
  }

  const summary = await getUserReportSummaryServer(session.userId);

  const cards = [
    { label: 'Submitted attempts', value: String(summary.total_attempts) },
    { label: 'Average score', value: formatScore(summary.avg_score) },
    { label: 'Best score', value: formatScore(summary.best_score) },
    { label: 'Total time', value: formatDuration(summary.total_time_seconds) },
  ];

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {cards.map((card) => (
          <Card key={card.label}>
            <CardHeader className="pb-1">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {card.label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">{card.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      {summary.most_recent ? (
        <p className="text-sm text-muted-foreground">
          Most recent: <span className="font-medium text-foreground">{summary.most_recent.test_name}</span>{' '}
          — {formatScore(summary.most_recent.score)} on {formatDateTime(summary.most_recent.submitted_at)}
        </p>
      ) : (
        <p className="text-sm text-muted-foreground">
          No submitted attempts yet — your scores will appear here after your first test.
        </p>
      )}
    </div>
  );
}
