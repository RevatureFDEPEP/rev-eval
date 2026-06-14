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
  init: { method?: string; body?: unknown } = {},
): Promise<Response> {
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

/**
 * Mint a quiz session server-side (W3-F3). The first (sanitized) question lands
 * in the initial HTML — no client spinner. Server-authoritative timing
 * (server_now/expires_at) and the sequential-reveal contract come from
 * test-management-service; the candidate never receives future question bodies.
 */
export async function mintSessionServer(testId: number): Promise<SessionResponse> {
  const response = await authedFetch('/v1/api/sessions/', {
    method: 'POST',
    body: { test_id: testId },
  });
  if (!response.ok) {
    throw new ServerApiError(response.status, response.statusText, await response.text());
  }
  return response.json();
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
