/**
 * <EmptyState> — shared zero-data placeholder (W4-F4 state-coverage audit).
 *
 * Distinct from loading and error states: a successful response that simply
 * has no rows. Gives actionable copy (and an optional CTA) instead of a blank
 * panel or a misleading spinner.
 */
import type { ComponentType, ReactNode } from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: ComponentType<{ className?: string }>;
  /** Optional CTA (e.g. a <Button> or <Link>). */
  action?: ReactNode;
}

export function EmptyState({ title, description, icon: Icon = Inbox, action }: EmptyStateProps) {
  return (
    <div
      data-testid="empty-state"
      className="flex flex-col items-center justify-center gap-2 py-12 text-center"
    >
      <Icon className="size-8 text-muted-foreground/60" />
      <p className="text-sm font-medium">{title}</p>
      <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
