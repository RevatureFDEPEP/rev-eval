/**
 * Base API Client
 *
 * Handles all HTTP requests to Next.js API routes (BFF pattern).
 * The BFF extracts the WorkOS access token and forwards to API Gateway.
 *
 * Architecture:
 * - Client calls Next.js API routes (browser automatically includes cookies)
 * - BFF (API routes) extracts JWT from WorkOS session using withAuth()
 * - BFF forwards request to API Gateway with Bearer token
 */

// Determine the base URL based on environment
function getBaseUrl(): string {
  // Server-side (Next.js server components)
  if (typeof window === 'undefined') {
    // In Docker, use localhost:3000 to call Next.js API from server components
    return process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';
  }

  // Client-side (browser) - use relative URL
  return '';
}

// Logging helper
const logApiCall = (method: string, endpoint: string, status?: number, error?: string) => {
  const timestamp = new Date().toISOString();
  if (error) {
    console.error(`🚨 [${timestamp}] API ${method} ${endpoint} - ERROR: ${error}`);
  } else {
    console.log(`🌐 [${timestamp}] API ${method} ${endpoint} - Status: ${status}`);
  }
};

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body: any
  ) {
    super(`API Error: ${status} ${statusText}`);
    this.name = 'ApiError';
  }
}

/**
 * Base fetch wrapper
 *
 * Authentication: Browser automatically includes cookies, BFF handles token extraction
 */
async function fetchApi(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  try {
    const baseUrl = getBaseUrl();
    const url = `${baseUrl}/api${endpoint}`;

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    const response = await fetch(url, {
      ...options,
      headers,
      credentials: 'include', // Always include cookies for authentication
    });

    // Log the API call
    logApiCall(options.method || 'GET', endpoint, response.status);

    if (!response.ok) {
      const body = await response.text();
      logApiCall(options.method || 'GET', endpoint, response.status, body);
      throw new ApiError(response.status, response.statusText, body);
    }

    return response;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    // Log network or other errors
    logApiCall(options.method || 'GET', endpoint, undefined, error instanceof Error ? error.message : 'Unknown error');
    throw error;
  }
}

/**
 * Generic API client methods
 *
 * These methods call Next.js API routes (BFF), not the API Gateway directly.
 * Authentication is handled by the Next.js API routes.
 */
export const api = {
  /**
   * GET request
   */
  async get<T>(endpoint: string): Promise<T> {
    const response = await fetchApi(endpoint, {
      method: 'GET',
    });

    return response.json();
  },

  /**
   * POST request
   */
  async post<T>(endpoint: string, data?: any): Promise<T> {
    const response = await fetchApi(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });

    return response.json();
  },

  /**
   * PUT request
   */
  async put<T>(endpoint: string, data: any): Promise<T> {
    const response = await fetchApi(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });

    return response.json();
  },

  /**
   * DELETE request
   */
  async delete<T>(endpoint: string): Promise<T> {
    const response = await fetchApi(endpoint, {
      method: 'DELETE',
    });

    return response.json();
  },
};
