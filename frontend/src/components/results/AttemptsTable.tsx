import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';
import { AttemptStatus, type Attempt } from '@/lib/api/types';
import { formatTableDate } from '@/lib/utils/date';
import { formatDuration, formatScore } from '@/lib/utils/format';

interface AttemptsTableProps {
  attempts: Attempt[];
  /** The attempt that brought the user here, highlighted in the table. */
  highlightSessionId?: string;
}

type BadgeVariant = 'default' | 'secondary' | 'destructive' | 'outline';

const STATUS_VARIANT: Record<AttemptStatus, BadgeVariant> = {
  [AttemptStatus.COMPLETED]: 'default',
  [AttemptStatus.SUBMITTED]: 'default',
  [AttemptStatus.ACTIVE]: 'secondary',
  [AttemptStatus.EXPIRED]: 'destructive',
  [AttemptStatus.ABANDONED]: 'destructive',
};

/**
 * Tabular breakdown region: one row per attempt with its result (status +
 * score) and time on task. The originating session is highlighted.
 */
export function AttemptsTable({ attempts, highlightSessionId }: AttemptsTableProps) {
  if (attempts.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center rounded-lg border border-dashed border-slate-200 text-sm text-slate-500">
        No attempts recorded yet.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <Table>
        <TableCaption className="sr-only">
          Your quiz attempts, one row per attempt.
        </TableCaption>
        <TableHeader>
          <TableRow>
            <TableHead className="w-12">#</TableHead>
            <TableHead>Date</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Score</TableHead>
            <TableHead className="text-right">Time</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {attempts.map((attempt, index) => {
            const isCurrent = attempt.session_id === highlightSessionId;
            return (
              <TableRow
                key={attempt.session_id}
                className={cn(isCurrent && 'bg-orange-50/80')}
              >
                <TableCell className="font-medium text-slate-500">{index + 1}</TableCell>
                <TableCell className="whitespace-nowrap">
                  {formatTableDate(attempt.created_at)}
                  {isCurrent && (
                    <span className="ml-2 text-xs font-medium text-orange-600">
                      This session
                    </span>
                  )}
                </TableCell>
                <TableCell>
                  <Badge variant={STATUS_VARIANT[attempt.status] ?? 'secondary'}>
                    {attempt.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-right font-semibold text-slate-900">
                  {formatScore(attempt.score)}
                </TableCell>
                <TableCell className="text-right text-slate-600">
                  {formatDuration(attempt.time_spent_seconds)}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
