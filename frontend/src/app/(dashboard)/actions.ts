'use server';

import { signOut } from '@workos-inc/authkit-nextjs';

/**
 * Server action for signing out
 * Can be used in client components
 */
export async function handleSignOut() {
  await signOut();
}
