/**
 * Server-side API client.
 * Used only inside Server Components; pulls the auth cookie via getSession()
 * and forwards the JWT to the API Gateway.
 */
import 'server-only';
import { getSession } from '@/lib/session';
import {
  AggregateReport,
  AuthIdentity,
  ReportAttemptsPage,
  ReportFilters,
  SessionOut,
  TimeseriesReport,
  TrainerDashboardStats,
  TrainerTestInfo,
  UserReportSummary,
} from './types';

const API_GATEWAY_URL = process.env.API_GATEWAY_URL || 'http://api-gateway:8000';

export class ServerApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body: unknown,
  ) {
    super(`Server API Error: ${status} ${statusText}`);
    this.name = 'ServerApiError';
  }
}

interface AuthedFetchInit {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
}

async function authedFetch(path: string, init: AuthedFetchInit = {}): Promise<Response> {
  const session = await getSession();
  if (!session) {
    throw new ServerApiError(401, 'Unauthorized', { error: 'No session cookie' });
  }
  return fetch(`${API_GATEWAY_URL}${path}`, {
    method: init.method ?? 'GET',
    headers: {
      Authorization: `Bearer ${session.token}`,
      'Content-Type': 'application/json',
    },
    body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
    cache: 'no-store',
  });
}

export async function getTrainerDashboardStatsServer(): Promise<TrainerDashboardStats> {
  const response = await authedFetch('/v1/api/dashboard/trainer/stats');
  if (!response.ok) {
    throw new ServerApiError(response.status, response.statusText, await response.text());
  }
  return response.json();
}

export async function getTrainerTestsServer(): Promise<TrainerTestInfo[]> {
  const response = await authedFetch('/v1/api/dashboard/trainer/tests');
  if (!response.ok) {
    throw new ServerApiError(response.status, response.statusText, await response.text());
  }
  return response.json();
}

/**
 * Mint a quiz session for a test (W3-F1 `POST /sessions`). Called server-side on
 * page render so the first question lands in the initial HTML — no client spinner.
 * Returns the server-authoritative timing + the first sanitized question.
 */
export async function mintSessionServer(testId: number): Promise<SessionOut> {
  const response = await authedFetch('/v1/api/sessions/', {
    method: 'POST',
    body: { test_id: testId },
  });
  if (!response.ok) {
    throw new ServerApiError(response.status, response.statusText, await response.text());
  }
  return response.json();
}

/**
 * Fetch the W4-F1 results summary envelope (`GET /v1/api/reports/user/{id}`).
 * Called server-side by the results page so the headline numbers land in the
 * initial HTML. A user with no submitted attempts gets a zeroed envelope.
 */
export async function getUserReportSummaryServer(userId: number): Promise<UserReportSummary> {
  const response = await authedFetch(`/v1/api/reports/user/${userId}`);
  if (!response.ok) {
    throw new ServerApiError(response.status, response.statusText, await response.text());
  }
  return response.json();
}

/**
 * Fetch a page of the user's attempt history
 * (`GET /v1/api/reports/user/{id}/attempts`), default sort `submitted_at:desc`.
 */
export async function getUserReportAttemptsServer(
  userId: number,
  opts: { page?: number; size?: number } = {},
): Promise<ReportAttemptsPage> {
  const params = new URLSearchParams();
  if (opts.page !== undefined) params.set('page', String(opts.page));
  if (opts.size !== undefined) params.set('size', String(opts.size));
  const qs = params.size > 0 ? `?${params.toString()}` : '';
  const response = await authedFetch(`/v1/api/reports/user/${userId}/attempts${qs}`);
  if (!response.ok) {
    throw new ServerApiError(response.status, response.statusText, await response.text());
  }
  return response.json();
}

/** Serialize shared trainer-report filters into a query string. */
function reportFilterParams(filters: ReportFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.testId !== undefined) params.set('test_id', String(filters.testId));
  if (filters.from) params.set('from', filters.from);
  if (filters.to) params.set('to', filters.to);
  return params.size > 0 ? `?${params.toString()}` : '';
}

/**
 * Fetch the W4-F3 per-test aggregate report (`GET /v1/api/reports/aggregate`).
 * TRAINER-gated — a non-trainer JWT yields 403 (surfaced via ServerApiError to
 * the section error boundary). Drives the dashboard's pass-rate bar chart.
 */
export async function getAggregateReportServer(
  filters: ReportFilters = {},
): Promise<AggregateReport> {
  const response = await authedFetch(`/v1/api/reports/aggregate${reportFilterParams(filters)}`);
  if (!response.ok) {
    throw new ServerApiError(response.status, response.statusText, await response.text());
  }
  return response.json();
}

/**
 * Fetch the W4-F4 attempt-volume timeseries (`GET /v1/api/reports/timeseries`),
 * granular by (day, test). TRAINER-gated. Drives the attempt-volume line chart;
 * the client sums across tests for a total or draws one line per quiz.
 */
export async function getTimeseriesServer(
  filters: ReportFilters = {},
): Promise<TimeseriesReport> {
  const response = await authedFetch(`/v1/api/reports/timeseries${reportFilterParams(filters)}`);
  if (!response.ok) {
    throw new ServerApiError(response.status, response.statusText, await response.text());
  }
  return response.json();
}

/**
 * Fetch the authenticated user's display identity (`GET /v1/api/auth/me`) to seed
 * the AuthContext server-side. Only id/email/role cross to the client — the raw
 * httpOnly cookie/token never enters the JS bundle.
 */
export async function getIdentityServer(): Promise<AuthIdentity> {
  const response = await authedFetch('/v1/api/auth/me');
  if (!response.ok) {
    throw new ServerApiError(response.status, response.statusText, await response.text());
  }
  const profile = (await response.json()) as { id: number; email: string; role: string };
  return { user_id: profile.id, email: profile.email, role: profile.role };
}
