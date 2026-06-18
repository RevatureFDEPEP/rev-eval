/**
 * Server-side API client.
 * Used only inside Server Components; pulls the auth cookie via getSession()
 * and forwards the JWT to the API Gateway.
 */
import 'server-only';
import { getSession } from '@/lib/session';
import {
  PaginatedAttempts,
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

async function authedFetch(path: string): Promise<Response> {
  const session = await getSession();
  if (!session) {
    throw new ServerApiError(401, 'Unauthorized', { error: 'No session cookie' });
  }
  return fetch(`${API_GATEWAY_URL}${path}`, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${session.token}`,
      'Content-Type': 'application/json',
    },
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
 * Summary envelope for a user's quiz attempts.
 * GET /reports/user/{userId} (reporting-and-analytics-service via the gateway).
 */
export async function getUserReportSummaryServer(
  userId: number,
): Promise<UserReportSummary> {
  const response = await authedFetch(`/reports/user/${userId}`);
  if (!response.ok) {
    throw new ServerApiError(response.status, response.statusText, await response.text());
  }
  return response.json();
}

/**
 * Paginated list of a user's attempts, used for the breakdown table and chart.
 * GET /reports/user/{userId}/attempts. Fetched oldest-first so the chart reads
 * left-to-right as a progression over time.
 */
export async function getUserAttemptsServer(
  userId: number,
  { size = 100, sort = 'created_at:asc' }: { size?: number; sort?: string } = {},
): Promise<PaginatedAttempts> {
  const params = new URLSearchParams({ size: String(size), sort });
  const response = await authedFetch(`/reports/user/${userId}/attempts?${params}`);
  if (!response.ok) {
    throw new ServerApiError(response.status, response.statusText, await response.text());
  }
  return response.json();
}
