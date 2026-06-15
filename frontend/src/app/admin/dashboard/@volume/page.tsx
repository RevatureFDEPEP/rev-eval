/**
 * Attempt-volume region (@volume slot) — async server component.
 * Reads the URL filters, fetches /reports/timeseries server-side, and renders
 * the attempt-volume line chart from the initial server data (no client fetch).
 */
import { getTimeseriesServer } from '@/lib/api/server';
import { parseReportFilters } from '@/lib/reports/transform';
import { Card, CardContent } from '@/components/ui/card';
import { AttemptVolumeChart } from '@/components/admin/AttemptVolumeChart';

interface VolumePageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function VolumePage({ searchParams }: VolumePageProps) {
  const filters = parseReportFilters(await searchParams);
  const report = await getTimeseriesServer(filters);

  return (
    <Card>
      <CardContent className="pt-6">
        <AttemptVolumeChart points={report.items} />
      </CardContent>
    </Card>
  );
}
