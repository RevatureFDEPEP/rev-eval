import { api } from './client';

export interface TestAggregateSummary {
  test_id: number;
  test_name: string;
  attempt_count: number;
  avg_score: number | null;
  pass_rate: number | null;
  median_score?: number | null;
}

export interface AggregateReportResponse {
  total_tests: number;
  page: number;
  page_size: number;
  tests: TestAggregateSummary[];
}

export async function getAggregateReport(size = 100): Promise<AggregateReportResponse> {
  return api.get<AggregateReportResponse>(`/v1/api/reports/aggregate?page=1&size=${size}`);
}
