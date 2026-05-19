import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { withAuth, getSignInUrl } from '@workos-inc/authkit-nextjs';
import { redirect } from 'next/navigation';

export default async function HomePage() {
  const { user } = await withAuth();
  
  // For now, we'll rely on the middleware to handle role-based routing
  // The session data is already processed by the middleware

  async function handleDirectLogin() {
    'use server';
    const signInUrl = await getSignInUrl();
    redirect(signInUrl);
  }
  return (
    <div className="min-h-screen bg-linear-to-br from-blue-50 to-indigo-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <header className="py-6">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold text-gray-900">Revature EvaluAI</h1>
            {user ? (
              <Link href="/dashboard">
                <Button>Go to Dashboard</Button>
              </Link>
            ) : (
              <form action={handleDirectLogin}>
                <Button type="submit">Sign In</Button>
              </form>
            )}
          </div>
        </header>

        {/* Hero Section */}
        <div className="text-center py-20">
          <h2 className="text-5xl font-bold text-gray-900 mb-6">
            AI-Powered Technical Assessments
          </h2>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            Streamline your evaluation process with intelligent test management, 
            automated scoring, and comprehensive analytics for trainers and students.
          </p>
          <div className="space-x-4">
            <form action={handleDirectLogin} className="inline">
              <Button type="submit" size="lg">Get Started</Button>
            </form>
            <Button variant="outline" size="lg">Learn More</Button>
          </div>
        </div>

        {/* Features */}
        <div className="py-20">
          <h3 className="text-3xl font-bold text-center text-gray-900 mb-12">
            Platform Features
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <Card>
              <CardHeader>
                <CardTitle>For Trainers</CardTitle>
                <CardDescription>Comprehensive test management</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li>• Create tests from templates</li>
                  <li>• Bulk assign to students</li>
                  <li>• AI-assisted scoring</li>
                  <li>• Detailed analytics</li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>For Students</CardTitle>
                <CardDescription>Seamless test experience</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li>• Quiz assessments and live interviews</li>
                  <li>• Real-time feedback</li>
                  <li>• Progress tracking</li>
                  <li>• Performance insights</li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>AI Integration</CardTitle>
                <CardDescription>Intelligent evaluation</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li>• AI-guided live interviews</li>
                  <li>• Automated scoring</li>
                  <li>• Plagiarism detection</li>
                  <li>• Performance analytics</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Test Authentication */}
        <div className="py-20 text-center">
          <Card className="max-w-md mx-auto">
            <CardHeader>
              <CardTitle>Test Authentication</CardTitle>
              <CardDescription>
                Try the authentication flow with WorkOS
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <p className="text-sm text-gray-600">
                  For testing purposes:
                </p>
                <ul className="text-sm text-gray-600 text-left">
                  <li>• Email with "trainer" → Trainer role</li>
                  <li>• Email with "admin" → Admin role</li>
                  <li>• Any other email → Associate role</li>
                </ul>
                <form action={handleDirectLogin}>
                  <Button type="submit" className="w-full">Test Login</Button>
                </form>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
