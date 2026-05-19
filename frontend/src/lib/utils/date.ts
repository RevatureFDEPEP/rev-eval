/**
 * Date utility functions with timezone support
 *
 * All dates from the backend are in UTC and need to be converted to the user's local timezone
 */

import { format, formatDistanceToNow, parseISO, isPast, isFuture } from 'date-fns';

// Regex to detect if a date string already contains timezone information
const TZ_REGEX = /(z|Z|[+-]\d{2}:?\d{2})$/;

// Regex for date-only strings without time
const DATE_ONLY_REGEX = /^\d{4}-\d{2}-\d{2}$/;

// Regex for datetime strings that use a space instead of "T"
const SPACE_SEPARATED_REGEX = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d+)?$/;

/**
 * Normalize a date string to ensure it is treated as UTC when parsed.
 * Adds missing "T" separator and "Z" suffix where necessary.
 */
function normalizeUtcString(dateString: string): string {
  let normalized = dateString.trim();

  if (!normalized) {
    return normalized;
  }

  if (DATE_ONLY_REGEX.test(normalized)) {
    normalized = `${normalized}T00:00:00`;
  } else if (SPACE_SEPARATED_REGEX.test(normalized)) {
    normalized = normalized.replace(' ', 'T');
  }

  if (!TZ_REGEX.test(normalized)) {
    normalized = `${normalized}Z`;
  }

  return normalized;
}

/**
 * Parse ISO date string and return Date object
 * Backend sends dates as ISO strings in UTC
 */
function parseDate(dateString: string | Date): Date {
  if (dateString instanceof Date) {
    return dateString;
  }
  return parseISO(normalizeUtcString(dateString));
}

/**
 * Format date and time in user's local timezone
 *
 * @param date - ISO date string or Date object
 * @param includeTime - Whether to include time (default: true)
 * @returns Formatted date string in user's local timezone
 *
 * @example
 * formatDateTime('2024-11-05T14:30:00Z') // "Nov 5, 2024 at 2:30 PM" (in user's timezone)
 * formatDateTime('2024-11-05T14:30:00Z', false) // "Nov 5, 2024"
 */
export function formatDateTime(date: string | Date | null | undefined, includeTime = true): string {
  if (!date) return '—';

  try {
    const parsedDate = parseDate(date);

    if (includeTime) {
      return format(parsedDate, 'MMM d, yyyy \'at\' h:mm a');
    }
    return format(parsedDate, 'MMM d, yyyy');
  } catch (error) {
    console.error('Error formatting date:', error);
    return '—';
  }
}

/**
 * Format date for display in tables (more compact)
 *
 * @param date - ISO date string or Date object
 * @returns Short formatted date string
 *
 * @example
 * formatTableDate('2024-11-05T14:30:00Z') // "11/5/24, 2:30 PM"
 */
export function formatTableDate(date: string | Date | null | undefined): string {
  if (!date) return '—';

  try {
    const parsedDate = parseDate(date);
    return format(parsedDate, 'M/d/yy, h:mm a');
  } catch (error) {
    console.error('Error formatting table date:', error);
    return '—';
  }
}

/**
 * Format relative time (e.g., "2 hours ago", "in 3 days")
 *
 * @param date - ISO date string or Date object
 * @returns Relative time string
 *
 * @example
 * formatRelativeTime('2024-11-05T14:30:00Z') // "2 hours ago"
 */
export function formatRelativeTime(date: string | Date | null | undefined): string {
  if (!date) return '—';

  try {
    const parsedDate = parseDate(date);
    return formatDistanceToNow(parsedDate, { addSuffix: true });
  } catch (error) {
    console.error('Error formatting relative time:', error);
    return '—';
  }
}

/**
 * Format due date with warning status
 * Returns formatted date and status indicator
 *
 * @param dueDate - ISO date string or Date object
 * @returns Object with formatted date and status
 *
 * @example
 * const { formatted, status, isOverdue } = formatDueDate('2024-11-10T23:59:59Z')
 * // { formatted: "Nov 10, 2024 at 11:59 PM", status: "upcoming", isOverdue: false }
 */
export function formatDueDate(dueDate: string | Date | null | undefined): {
  formatted: string;
  status: 'overdue' | 'urgent' | 'upcoming' | 'none';
  isOverdue: boolean;
  isUrgent: boolean;
} {
  if (!dueDate) {
    return {
      formatted: 'No due date',
      status: 'none',
      isOverdue: false,
      isUrgent: false,
    };
  }

  try {
    const parsedDate = parseDate(dueDate);
    const now = new Date();
    const hoursUntilDue = (parsedDate.getTime() - now.getTime()) / (1000 * 60 * 60);

    const isOverdue = isPast(parsedDate);
    const isUrgent = !isOverdue && hoursUntilDue <= 24; // Less than 24 hours

    let status: 'overdue' | 'urgent' | 'upcoming' | 'none';
    if (isOverdue) {
      status = 'overdue';
    } else if (isUrgent) {
      status = 'urgent';
    } else {
      status = 'upcoming';
    }

    return {
      formatted: formatDateTime(parsedDate),
      status,
      isOverdue,
      isUrgent,
    };
  } catch (error) {
    console.error('Error formatting due date:', error);
    return {
      formatted: '—',
      status: 'none',
      isOverdue: false,
      isUrgent: false,
    };
  }
}

/**
 * Check if a date is in the past
 *
 * @param date - ISO date string or Date object
 * @returns true if date is in the past
 */
export function isDatePast(date: string | Date | null | undefined): boolean {
  if (!date) return false;

  try {
    const parsedDate = parseDate(date);
    return isPast(parsedDate);
  } catch (error) {
    console.error('Error checking if date is past:', error);
    return false;
  }
}

/**
 * Check if a date is in the future
 *
 * @param date - ISO date string or Date object
 * @returns true if date is in the future
 */
export function isDateFuture(date: string | Date | null | undefined): boolean {
  if (!date) return false;

  try {
    const parsedDate = parseDate(date);
    return isFuture(parsedDate);
  } catch (error) {
    console.error('Error checking if date is future:', error);
    return false;
  }
}

/**
 * Format timestamp for display (full date and time)
 * Used for created_at, updated_at, submitted_at fields
 *
 * @param timestamp - ISO date string or Date object
 * @returns Formatted timestamp string
 *
 * @example
 * formatTimestamp('2024-11-05T14:30:00Z') // "November 5, 2024 at 2:30:00 PM"
 */
export function formatTimestamp(timestamp: string | Date | null | undefined): string {
  if (!timestamp) return '—';

  try {
    const parsedDate = parseDate(timestamp);
    return format(parsedDate, 'MMMM d, yyyy \'at\' h:mm:ss a');
  } catch (error) {
    console.error('Error formatting timestamp:', error);
    return '—';
  }
}
