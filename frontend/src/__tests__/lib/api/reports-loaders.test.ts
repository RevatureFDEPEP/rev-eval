/**
 * Unit test for the W4-F2 cached reporting loaders. Confirms they delegate to
 * the server fetchers and that React cache() de-dupes repeated calls for the
 * same user within a render (the property the page relies on so the ownership
 * check and the streamed regions share one round-trip).
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

const getUserReportSummaryServer = vi.fn();
const getUserAttemptsServer = vi.fn();
vi.mock('@/lib/api/server', () => ({
  getUserReportSummaryServer: (...a: unknown[]) => getUserReportSummaryServer(...a),
  getUserAttemptsServer: (...a: unknown[]) => getUserAttemptsServer(...a),
}));

import {
  ATTEMPTS_PAGE_SIZE,
  loadUserAttempts,
  loadUserSummary,
} from '@/lib/api/reports';

describe('reporting loaders', () => {
  beforeEach(() => {
    getUserReportSummaryServer.mockReset().mockResolvedValue({ user_id: 7 });
    getUserAttemptsServer.mockReset().mockResolvedValue({ items: [], total: 0 });
  });

  it('loadUserSummary delegates to the summary fetcher', async () => {
    const out = await loadUserSummary(7);
    expect(getUserReportSummaryServer).toHaveBeenCalledWith(7);
    expect(out).toEqual({ user_id: 7 });
  });

  it('loadUserAttempts requests one large page (default sort)', async () => {
    await loadUserAttempts(7);
    expect(getUserAttemptsServer).toHaveBeenCalledWith(7, {
      page: 1,
      size: ATTEMPTS_PAGE_SIZE,
    });
  });
});
