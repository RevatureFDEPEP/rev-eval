/**
 * Pass-rate region (@passrate slot) — async server component.
 * Reads the URL filters, fetches /reports/aggregate server-side, and renders
 * the pass-rate bar chart from the initial server data (no client fetch).
 */
import { getAggregateReportServer } from '@/lib/api/server';
import { parseReportFilters } from '@/lib/reports/transform';
import { Card, CardContent } from '@/components/ui/card';
import { PassRateBarChart } from '@/components/admin/PassRateBarChart';

interface PassRatePageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function PassRatePage({ searchParams }: PassRatePageProps) {
  const filters = parseReportFilters(await searchParams);
  const report = await getAggregateReportServer(filters);

  return (
    <Card>
      <CardContent className="pt-6">
        <PassRateBarChart rows={report.items} passThreshold={report.pass_threshold} />
      </CardContent>
    </Card>
  );
}
