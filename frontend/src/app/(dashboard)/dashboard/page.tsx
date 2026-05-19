import { redirect } from 'next/navigation';
import { withAuth } from '@workos-inc/authkit-nextjs';

export default async function DashboardPage() {
  const { user } = await withAuth();
  
  if (!user) {
    redirect('/auth/login');
  }
 
  console.log('user', user);
  
  // The middleware will handle the role-based routing automatically
  // This page should never be reached because middleware redirects based on role
  // But if it is reached, redirect to associate dashboard as fallback
  redirect('/participant/dashboard');
}
