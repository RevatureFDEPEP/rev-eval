/**
 * Server-side API client.
 * Used only inside Server Components; pulls the auth cookie via getSession()
 * and forwards the JWT to the API Gateway.
 */
import 'server-only';
import { getSession } from '@/lib/session';
import { SessionResponse, TrainerDashboardStats, TrainerTestInfo } from './types';

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

async function authedFetch(
  path: string,
  init?: { method?: string; body?: unknown },
): Promise<Response> {
  const session = await getSession();
  if (!session) {
    throw new ServerApiError(401, 'Unauthorized', { error: 'No session cookie' });
  }
  return fetch(`${API_GATEWAY_URL}${path}`, {
    method: init?.method ?? 'GET',
    headers: {
      Authorization: `Bearer ${session.token}`,
      'Content-Type': 'application/json',
    },
    body: init?.body !== undefined ? JSON.stringify(init.body) : undefined,
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
 * Mint a quiz session for the given test, server-side, so the first question is
 * in the initial HTML (no client spinner). POST /v1/api/sessions (W3-F1).
 */
export async function createSessionServer(testId: number): Promise<SessionResponse> {
  const response = await authedFetch('/v1/api/sessions', {
    method: 'POST',
    body: { test_id: testId },
  });
  if (!response.ok) {
    throw new ServerApiError(response.status, response.statusText, await response.text());
  }
  return response.json();
}
