/**
 * AttemptsTable (W4-F2) — the breakdown region of the results page.
 *
 * The spec describes "one row per question", but W4-F1 exposes per-attempt rows
 * only (ADR 0001), so this renders one row per attempt: test, status, score,
 * correct/total, time, and submission time. The attempt the page links to
 * (`featuredSessionId`) is highlighted and marked `aria-current`.
 */
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';
import {
  formatDateTime,
  formatDuration,
  formatScorePct,
} from '@/lib/results/format';
import type { ReportAttemptItem, ReportSessionStatus } from '@/lib/api/types';

const STATUS_VARIANT: Record<
  ReportSessionStatus,
  'default' | 'secondary' | 'outline'
> = {
  SUBMITTED: 'default',
  ACTIVE: 'secondary',
  EXPIRED: 'outline',
};

export function AttemptsTable({
  attempts,
  featuredSessionId,
}: {
  attempts: ReportAttemptItem[];
  featuredSessionId?: string;
}) {
  return (
    <section aria-labelledby="attempts-heading" className="space-y-3">
      <h2 id="attempts-heading" className="text-lg font-semibold text-slate-900">
        Attempt history
      </h2>
      {attempts.length === 0 ? (
        <p className="rounded-md border border-dashed border-slate-200 p-6 text-center text-sm text-slate-500">
          You haven&apos;t completed any quizzes yet.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Test</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Score</TableHead>
                <TableHead className="text-right">Correct</TableHead>
                <TableHead className="text-right">Time</TableHead>
                <TableHead>Submitted</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {attempts.map((a) => {
                const featured = a.session_id === featuredSessionId;
                return (
                  <TableRow
                    key={a.session_id}
                    aria-current={featured ? 'true' : undefined}
                    className={cn(featured && 'bg-blue-50 font-medium')}
                  >
                    <TableCell>{a.test_name ?? `Test ${a.test_id}`}</TableCell>
                    <TableCell>
                      <Badge variant={STATUS_VARIANT[a.status]}>{a.status}</Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {formatScorePct(a.score)}
                    </TableCell>
                    <TableCell className="text-right">
                      {a.correct_count}/{a.total_answered}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatDuration(a.time_spent_seconds)}
                    </TableCell>
                    <TableCell>{formatDateTime(a.submitted_at)}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </section>
  );
}
