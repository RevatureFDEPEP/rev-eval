/** Suspense skeleton for the pass-rate panel (W4-F4). */
import { Card, CardContent } from '@/components/ui/card';

export default function PassRateLoading() {
  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div className="h-4 w-40 animate-pulse rounded bg-muted" />
        <div className="h-[280px] w-full animate-pulse rounded bg-muted" />
      </CardContent>
    </Card>
  );
}
