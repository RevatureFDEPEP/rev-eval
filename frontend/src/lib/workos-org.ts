import { WorkOS } from '@workos-inc/node';

// Initialize WorkOS client
const workos = new WorkOS(process.env.WORKOS_API_KEY);

/**
 * Automatically adds a user to the default organization if they're not already a member
 * @param userId - WorkOS user ID
 * @param email - User's email address
 * @param firstName - User's first name
 * @param lastName - User's last name
 * @returns Promise<boolean> - true if user was added or already exists
 */
export async function ensureUserInOrganization(
  userId: string,
  email: string,
  firstName?: string,
  lastName?: string
): Promise<boolean> {
  try {
    const organizationId = process.env.WORKOS_DEFAULT_ORG;
    
    if (!organizationId) {
      console.warn('WORKOS_DEFAULT_ORG not set, skipping organization assignment');
      return false;
    }

    // Check if user is already in the organization
    const memberships = await workos.userManagement.listOrganizationMemberships({
      userId,
    });

    const isAlreadyMember = memberships.data.some(
      membership => membership.organizationId === organizationId
    );

    if (isAlreadyMember) {
      console.log(`User ${email} is already a member of organization ${organizationId}`);
      return true;
    }

    // Add user to the organization (role assignment handled separately)
    await workos.userManagement.createOrganizationMembership({
      userId,
      organizationId,
    });

    console.log(`Successfully added user ${email} to organization ${organizationId}`);
    return true;
  } catch (error) {
    console.error('Error adding user to organization:', error);
    return false;
  }
}

/**
 * Updates a user's role in the organization
 * @param userId - WorkOS user ID
 * @param role - New role ('org-trainer', 'org-participant', 'org-admin')
 * @returns Promise<boolean> - true if role was updated successfully
 */
export async function updateUserRole(
  userId: string,
  role: 'org-trainer' | 'org-participant' | 'org-admin'
): Promise<boolean> {
  try {
    const organizationId = process.env.WORKOS_DEFAULT_ORG;
    
    if (!organizationId) {
      console.warn('WORKOS_DEFAULT_ORG not set, cannot update role');
      return false;
    }

    // Get user's organization memberships
    const memberships = await workos.userManagement.listOrganizationMemberships({
      userId,
    });

    const membership = memberships.data.find(
      m => m.organizationId === organizationId
    );

    if (!membership) {
      console.error(`User ${userId} is not a member of organization ${organizationId}`);
      return false;
    }

    // Update the membership role
    await workos.userManagement.updateOrganizationMembership(
      membership.id,
      { roleSlug: role }
    );

    console.log(`Successfully updated user ${userId} role to ${role}`);
    return true;
  } catch (error) {
    console.error('Error updating user role:', error);
    return false;
  }
}

/**
 * Determines user role based on email pattern and adds them to organization
 * @param email - User's email address
 * @returns Promise<string> - Role to assign ('org-trainer', 'org-participant', 'org-admin')
 */
export function determineRoleFromEmail(email: string): 'org-trainer' | 'org-participant' | 'org-admin' {
  const emailLower = email.toLowerCase();
  
  if (emailLower.includes('trainer') || emailLower.includes('instructor')) {
    return 'org-trainer';
  }
  
  if (emailLower.includes('admin')) {
    return 'org-admin';
  }
  
  return 'org-participant'; // Default role
}
