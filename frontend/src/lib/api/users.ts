/**
 * Users API
 *
 * Functions for managing users and profiles.
 */

import { api } from './client';
import type { User } from './types';

/**
 * Get current authenticated user's profile
 */
export async function getCurrentUser(): Promise<User> {
  return api.get<User>('/v1/api/users/me');
}

/**
 * Get user by database id.
 */
export async function getUserById(userId: number): Promise<User> {
  return api.get<User>(`/v1/api/users/${userId}`);
}

/**
 * Get user by email
 */
export async function getUserByEmail(email: string): Promise<User> {
  return api.get<User>(`/v1/api/users/by-email/${email}`);
}
