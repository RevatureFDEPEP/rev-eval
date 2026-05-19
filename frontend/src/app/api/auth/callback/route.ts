import { handleAuth } from '@workos-inc/authkit-nextjs';
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  // Let WorkOS handle the auth callback
  const response = await handleAuth({ returnPathname: '/dashboard' })(request);

  // If it's a redirect, fix the Location header to use the correct host
  if (response instanceof NextResponse && response.headers.has('location')) {
    const location = response.headers.get('location');

    // Check if it's redirecting to localhost
    if (location && location.includes('localhost:3000')) {
      // Get the correct host from request headers (ALB sets X-Forwarded-Host)
      const forwardedHost = request.headers.get('x-forwarded-host') || request.headers.get('host');
      const forwardedProto = request.headers.get('x-forwarded-proto') || 'https';

      console.log('Debug headers:', {
        forwardedHost,
        forwardedProto,
        host: request.headers.get('host'),
        allHeaders: Object.fromEntries(request.headers.entries())
      });

      if (forwardedHost) {
        // Replace localhost:3000 with the actual host (handle both http and https)
        const correctUrl = location
          .replace('https://localhost:3000', `${forwardedProto}://${forwardedHost}`)
          .replace('http://localhost:3000', `${forwardedProto}://${forwardedHost}`);

        console.log('Fixing redirect URL:', { original: location, corrected: correctUrl });

        // Create new response with corrected location
        return NextResponse.redirect(correctUrl);
      }
    }
  }

  return response;
}