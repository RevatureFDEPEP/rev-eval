/**
 * ConnectionStatus Component
 *
 * Displays WebSocket connection status with visual indicators.
 * Shows connecting, connected, disconnected, or error states.
 */

'use client';

import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Wifi, WifiOff, Loader2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ConnectionStatusProps {
  state: 'disconnected' | 'connecting' | 'connected' | 'error';
  className?: string;
}

export function ConnectionStatus({ state, className }: ConnectionStatusProps) {
  const getStatusConfig = () => {
    switch (state) {
      case 'connected':
        return {
          icon: <Wifi className="size-3" />,
          label: 'Connected',
          color: 'bg-green-100 text-green-700 border-green-300',
          tooltip: 'Connection active',
        };
      case 'connecting':
        return {
          icon: <Loader2 className="size-3 animate-spin" />,
          label: 'Connecting',
          color: 'bg-blue-100 text-blue-700 border-blue-300',
          tooltip: 'Establishing connection...',
        };
      case 'error':
        return {
          icon: <AlertCircle className="size-3" />,
          label: 'Error',
          color: 'bg-red-100 text-red-700 border-red-300',
          tooltip: 'Connection failed. Please refresh.',
        };
      case 'disconnected':
      default:
        return {
          icon: <WifiOff className="size-3" />,
          label: 'Disconnected',
          color: 'bg-slate-100 text-slate-700 border-slate-300',
          tooltip: 'Not connected',
        };
    }
  };

  const config = getStatusConfig();

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className={cn(
              'flex items-center gap-1.5 px-2 py-1 text-xs font-medium shadow-sm transition-all',
              config.color,
              className
            )}
          >
            {config.icon}
            <span>{config.label}</span>
          </Badge>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="text-xs">
          <p>{config.tooltip}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
