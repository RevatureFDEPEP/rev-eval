/**
 * Server-side API client.
 * Used only inside Server Components; pulls the auth cookie via getSession()
 * and forwards the JWT to the API Gateway.
 */
import 'server-only';
import { getSession } from '@/lib/session';
import {
  AuthIdentity,
  SessionOut,
  TrainerDashboardStats,
  TrainerTestInfo,
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
