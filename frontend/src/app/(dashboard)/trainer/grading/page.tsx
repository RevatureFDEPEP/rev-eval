'use client';

import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth/useAuth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';
import { getGradingQueue, type PendingAnswer } from '@/lib/api';
import { GradeAnswerSheet } from '@/components/trainer/GradeAnswerSheet';
import { formatTableDate } from '@/lib/utils/date';

/**
 * Trainer "to grade" queue (W5-F1): free-text answers awaiting a manual grade.
 * Selecting one opens the grading sheet; grading refreshes the queue.
 */
export default function TrainerGradingPage() {
  const { user, loading: authLoading } = useAuth({ ensureSignedIn: true });

  const [items, setItems] = useState<PendingAnswer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<PendingAnswer | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const queue = await getGradingQueue({ page: 1, size: 50 });
      setItems(queue.items);
    } catch {
      setError('Failed to load the grading queue');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading || !user) return;
    void load();
  }, [authLoading, user, load]);

  return (
    <div className="space-y-4 p-4">
      <div>
        <h1 className="text-2xl font-semibold">Answers to grade</h1>
        <p className="text-muted-foreground text-sm">
          Free-text answers awaiting a manual grade.
        </p>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading…
        </div>
      ) : error ? (
        <p className="text-destructive text-sm">{error}</p>
      ) : items.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          Nothing to grade — all caught up.
        </p>
      ) : (
        <div className="space-y-3">
          {items.map((a) => (
            <Card key={a.answer_id}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">
                  {a.test_name ?? `Test #${a.test_id}`} · participant {a.user_id}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex items-center justify-between gap-4">
                <div className="min-w-0 text-sm">
                  <p className="truncate">
                    {a.question_text ?? a.question_id}
                  </p>
                  <p className="text-muted-foreground">
                    Submitted {a.submitted_at ? formatTableDate(a.submitted_at) : '—'}
                  </p>
                </div>
                <Button
                  size="sm"
                  onClick={() => {
                    setSelected(a);
                    setSheetOpen(true);
                  }}
                >
                  Grade
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <GradeAnswerSheet
        answer={selected}
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        onGraded={load}
      />
    </div>
  );
}
