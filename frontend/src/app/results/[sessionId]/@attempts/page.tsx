/**
 * Attempts table region (@attempts slot) — async server component.
 *
 * Fetches the first page of the user's attempt history (W4-F1
 * GET /reports/user/{userId}/attempts, default sort submitted_at:desc) and
 * renders one row per attempt. The row matching the [sessionId] route param
 * is highlighted as “this attempt”.
 */
import { redirect } from 'next/navigation';
import { getSession } from '@/lib/session';
import { getUserReportAttemptsServer } from '@/lib/api/server';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';
import { formatTableDate } from '@/lib/utils/date';
import { formatDuration, formatScore } from '@/lib/utils/duration';
import type { ReportSessionStatus } from '@/lib/api/types';

const STATUS_VARIANT: Record<ReportSessionStatus, 'default' | 'secondary' | 'outline'> = {
  SUBMITTED: 'default',
  ACTIVE: 'secondary',
  EXPIRED: 'outline',
};

interface AttemptsPageProps {
  params: Promise<{ sessionId: string }>;
}

export default async function AttemptsTablePage({ params }: AttemptsPageProps) {
  const { sessionId } = await params;

  const session = await getSession();
  if (!session) {
    redirect('/');
  }

  const attempts = await getUserReportAttemptsServer(session.userId, { page: 1, size: 20 });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          Attempt history
          <span className="ml-2 text-sm font-normal text-muted-foreground">
            {attempts.total} total
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {attempts.items.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            No attempts yet — take a test and it will show up here.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Test</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Started</TableHead>
                <TableHead className="text-right">Duration</TableHead>
                <TableHead className="text-right">Score</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {attempts.items.map((attempt) => {
                const isCurrent = attempt.session_id === sessionId;
                return (
                  <TableRow
                    key={attempt.session_id}
                    className={cn(isCurrent && 'bg-accent/60 hover:bg-accent/60')}
                    data-current={isCurrent || undefined}
                  >
                    <TableCell className="font-medium">
                      {attempt.test_name}
                      {isCurrent && (
                        <span className="ml-2 text-xs text-muted-foreground">(this attempt)</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant={STATUS_VARIANT[attempt.status]}>{attempt.status}</Badge>
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-muted-foreground">
                      {formatTableDate(attempt.started_at)}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {formatDuration(attempt.duration_seconds)}
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {formatScore(attempt.score)}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
