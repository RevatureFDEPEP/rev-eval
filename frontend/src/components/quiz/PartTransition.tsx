/**
 * Part Transition Component
 *
 * Full-screen loading overlay displayed during Part A to Part B transition.
 * Shows while submitting Part A answers and fetching Part B questions.
 */

'use client';

import { Loader2 } from 'lucide-react';

interface PartTransitionProps {
  message?: string;
}

export function PartTransition({ message = 'Loading next part...' }: PartTransitionProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-white/90 backdrop-blur-sm">
      <div className="flex flex-col items-center gap-4 rounded-lg bg-white p-8 shadow-lg">
        <Loader2 className="size-12 animate-spin text-blue-600" />
        <div className="text-center">
          <p className="text-lg font-medium text-slate-900">{message}</p>
          <p className="mt-1 text-sm text-slate-600">Please wait while we prepare your test...</p>
        </div>
      </div>
    </div>
  );
}
