/**
 * Server-Side API Client
 *
 * This client is used ONLY in Server Components.
 * It calls the API Gateway directly with the WorkOS access token.
 */

import { withAuth } from '@workos-inc/authkit-nextjs';
import { TrainerDashboardStats, TrainerTestInfo } from './types';

const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://api-gateway:8000';

export class ServerApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body: any
  ) {
    super(`Server API Error: ${status} ${statusText}`);
    this.name = 'ServerApiError';
  }
}

/**
 * Get trainer dashboard statistics
 * ONLY use in Server Components
 */
export async function getTrainerDashboardStatsServer(): Promise<TrainerDashboardStats> {
  try {
    // Extract token using withAuth (works in server components)
    const { accessToken } = await withAuth();

    if (!accessToken) {
      throw new Error('No access token available');
    }

    const response = await fetch(`${API_GATEWAY_URL}/v1/api/dashboard/trainer/stats`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      cache: 'no-store', // Don't cache dashboard data
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new ServerApiError(response.status, response.statusText, errorText);
    }

    return response.json();
  } catch (error) {
    console.error('[Server API] Error fetching trainer stats:', error);
    throw error;
  }
}

/**
 * Get trainer tests
 * ONLY use in Server Components
 */
export async function getTrainerTestsServer(): Promise<TrainerTestInfo[]> {
  try {
    // Extract token using withAuth (works in server components)
    const { accessToken } = await withAuth();

    if (!accessToken) {
      throw new Error('No access token available');
    }

    const response = await fetch(`${API_GATEWAY_URL}/v1/api/dashboard/trainer/tests`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      cache: 'no-store', // Don't cache dashboard data
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new ServerApiError(response.status, response.statusText, errorText);
    }

    return response.json();
  } catch (error) {
    console.error('[Server API] Error fetching trainer tests:', error);
    throw error;
  }
}
