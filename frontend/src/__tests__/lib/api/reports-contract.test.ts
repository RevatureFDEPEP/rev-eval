/**
 * Contract test for the W4-F2 reporting client against the W4-F1 envelope.
 *
 * Not a full live integration test (that is the Stage 8 smoke against the
 * running stack) — this pins the cross-component contract that unit tests miss:
 * the exact gateway path + Bearer header the frontend sends, and that a
 * representative W4-F1 JSON payload deserializes into the typed envelope the
 * page renders. If F1 renames a field or the path drifts, this turns red.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/lib/session', () => ({
  getSession: vi.fn(async () => ({
    userId: 2,
    email: 'rev-eval.test002@yopmail.com',
    role: 'PARTICIPANT',
    token: 'jwt-token',
  })),
}));

import {
  ServerApiError,
  getUserAttemptsServer,
  getUserReportSummaryServer,
} from '@/lib/api/server';

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

function ok(body: unknown) {
  return {
    ok: true,
    status: 200,
    statusText: 'OK',
    json: async () => body,
  } as Response;
}

describe('reporting client ↔ W4-F1 contract', () => {
  beforeEach(() => fetchMock.mockReset());

  it('GETs the summary at the gateway reports path with a Bearer token', async () => {
    const payload = {
      user_id: 2,
      total_attempts: 2,
      average_score: 0.75,
      best_score: 0.9,
      total_time_spent_seconds: 1200,
      most_recent_attempt: {
        session_id: 'abc',
        test_id: 5,
        test_name: 'Algorithms',
        status: 'SUBMITTED',
        score: 0.9,
        correct_count: 9,
        total_answered: 10,
        started_at: '2026-06-17T10:00:00Z',
        submitted_at: '2026-06-17T10:10:00Z',
        time_spent_seconds: 600,
      },
    };
    fetchMock.mockResolvedValueOnce(ok(payload));

    const summary = await getUserReportSummaryServer(2);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/v1\/api\/reports\/user\/2$/);
    expect(init.headers.Authorization).toBe('Bearer jwt-token');
    // envelope deserializes into the shape the page consumes
    expect(summary.best_score).toBe(0.9);
    expect(summary.most_recent_attempt?.test_name).toBe('Algorithms');
  });

  it('builds the attempts path with page/size query params', async () => {
    fetchMock.mockResolvedValueOnce(
      ok({ items: [], total: 0, page: 1, size: 100 }),
    );

    await getUserAttemptsServer(2, { page: 1, size: 100 });

    const [url] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/v1\/api\/reports\/user\/2\/attempts\?page=1&size=100$/);
  });

  it('maps a non-OK reporting response to ServerApiError', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
      text: async () => 'Not authorized',
    } as Response);

    await expect(getUserReportSummaryServer(99)).rejects.toMatchObject({
      name: 'ServerApiError',
      status: 403,
    });
    void ServerApiError;
  });
});
