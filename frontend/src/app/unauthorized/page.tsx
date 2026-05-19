import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle } from 'lucide-react';

export default function UnauthorizedPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
            <AlertTriangle className="h-6 w-6 text-red-600" />
          </div>
          <CardTitle className="text-2xl font-bold text-gray-900">Access Denied</CardTitle>
          <CardDescription>
            You don't have permission to access this resource
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-center text-sm text-gray-600">
            <p>Your current role doesn't have access to this page.</p>
            <p>Please contact your administrator if you believe this is an error.</p>
          </div>
          <div className="space-y-2">
            <Link href="/" className="block">
              <Button className="w-full">Go to Home</Button>
            </Link>
            <Link href="/auth/login" className="block">
              <Button variant="outline" className="w-full">Sign In Again</Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
