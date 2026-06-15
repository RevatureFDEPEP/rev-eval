/** Suspense skeleton for the attempt-volume panel (W4-F4). */
import { Card, CardContent } from '@/components/ui/card';

export default function VolumeLoading() {
  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div className="h-4 w-44 animate-pulse rounded bg-muted" />
        <div className="h-[280px] w-full animate-pulse rounded bg-muted" />
      </CardContent>
    </Card>
  );
}
