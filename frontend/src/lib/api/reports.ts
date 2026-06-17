/**
 * Reporting & Analytics API — candidate-facing reporting.
 *
 * Talks to the reporting-and-analytics-service `/v1/api/reports` contract
 * through the BFF + gateway. The candidate endpoints are self-readable
 * (a participant may read their own report) or trainer/admin read-any; the
 * gateway-verified identity is enforced server-side.
 */
import { api } from './client';

export interface ScoreStats {
  count: number;
  min: number | null;
  max: number | null;
  average: number | null;
  median: number | null;
}

/** Summary of one candidate's attempts. Matches backend `CandidateReport`. */
export interface CandidateReport {
  user_id: number;
  assigned: number;
  completed: number;
  in_progress: number;
  by_status: Record<string, number>;
  average_final_score: number | null;
  best_score: number | null;
  score: ScoreStats;
}

/** One attempt row. Matches backend `AttemptEntry`. */
export interface AttemptEntry {
  submission_id: number | null;
  test_id: number | null;
  test_name: string | null;
  status: string | null;
  score: number | null;
  assigned_at: string | null;
  submitted_at: string | null;
}

/** A page of attempts with the applied query echoed back. */
export interface PaginatedAttempts {
  user_id: number;
  total: number;
  page: number;
  page_size: number;
  sort: string;
  order: string;
  status: string | null;
  items: AttemptEntry[];
}

export interface AttemptsQuery {
  page?: number;
  page_size?: number;
  status?: string;
  sort?: 'submitted_at' | 'assigned_at' | 'score' | 'test_name' | 'status';
  order?: 'asc' | 'desc';
}

/** Fetch a candidate's summary report (self-read or trainer/admin). */
export async function getCandidateReport(userId: number): Promise<CandidateReport> {
  return api.get<CandidateReport>(`/v1/api/reports/user/${userId}`);
}

/** Fetch a candidate's attempts, paginated/filtered/sorted (self-read or trainer/admin). */
export async function getCandidateAttempts(
  userId: number,
  query: AttemptsQuery = {},
): Promise<PaginatedAttempts> {
  const params = new URLSearchParams();
  if (query.page !== undefined) params.append('page', String(query.page));
  if (query.page_size !== undefined) params.append('page_size', String(query.page_size));
  if (query.status) params.append('status', query.status);
  if (query.sort) params.append('sort', query.sort);
  if (query.order) params.append('order', query.order);

  const qs = params.toString();
  return api.get<PaginatedAttempts>(
    `/v1/api/reports/user/${userId}/attempts${qs ? `?${qs}` : ''}`,
  );
}
