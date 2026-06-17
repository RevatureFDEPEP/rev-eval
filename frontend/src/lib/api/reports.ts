/**
 * Per-render memoized loaders for the candidate results page (W4-F2).
 *
 * The page validates session ownership up front AND streams three independent
 * regions (summary, attempts table, chart), several of which need the same
 * data. `authedFetch` sets `cache: 'no-store'`, so Next's fetch de-dup does not
 * apply; React `cache()` collapses repeated calls within a single server render
 * into one request (and shares a thrown error), so a region can re-request what
 * the page already loaded without a second round-trip to the gateway.
 */
import 'server-only';
import { cache } from 'react';
import {
  getUserAttemptsServer,
  getUserReportSummaryServer,
} from '@/lib/api/server';

/**
 * Largest attempt page the results view requests. The breakdown table and chart
 * render the candidate's history from a single fetch; a featured session beyond
 * this window cannot be confirmed (see the page's ownership check). Realistic
 * candidate attempt counts sit far below this, so no pagination UI is built.
 */
export const ATTEMPTS_PAGE_SIZE = 100;

export const loadUserSummary = cache((userId: number) =>
  getUserReportSummaryServer(userId),
);

export const loadUserAttempts = cache((userId: number) =>
  getUserAttemptsServer(userId, { page: 1, size: ATTEMPTS_PAGE_SIZE }),
);
