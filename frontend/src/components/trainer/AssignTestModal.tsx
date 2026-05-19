"use client";

import { useEffect, useMemo, useState } from 'react';
import { ChevronDownIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { cn } from '@/lib/utils';
import { formatTableDate } from '@/lib/utils/date';
import { bulkAssignTest } from '@/lib/api';
import { TrainerTestInfo } from '@/lib/api/types';
import { toast } from 'sonner';

const getFriendlyType = (type: string) => (type === 'MCQ' || type === 'QUIZ' ? 'Quiz' : 'Interview');

interface AssignTestModalProps {
  tests: TrainerTestInfo[];
  onSuccess?: () => void;
  triggerClassName?: string;
  defaultTestId?: number;
  hideTestSelection?: boolean; // Hide test dropdown when viewing test details
}

export function AssignTestModal({ tests, onSuccess, triggerClassName, defaultTestId, hideTestSelection }: AssignTestModalProps) {
  const [open, setOpen] = useState(false);
  const [selectedTestId, setSelectedTestId] = useState<string>(defaultTestId ? `${defaultTestId}` : '');
  const [participantEmails, setParticipantEmails] = useState('');
  const [datePickerOpen, setDatePickerOpen] = useState(false);
  const [dueDate, setDueDate] = useState<Date | undefined>(undefined);
  const [dueTime, setDueTime] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const options = useMemo(() => (tests.length ? tests : []), [tests]);
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const isDueDateToday = Boolean(
    dueDate &&
      dueDate.getFullYear() === now.getFullYear() &&
      dueDate.getMonth() === now.getMonth() &&
      dueDate.getDate() === now.getDate()
  );
  const minSelectableTime = `${String(now.getHours()).padStart(2, '0')}:${String(
    now.getMinutes()
  ).padStart(2, '0')}`;

  useEffect(() => {
    if (defaultTestId) {
      setSelectedTestId(`${defaultTestId}`);
    }
  }, [defaultTestId, open]);

  useEffect(() => {
    if (!dueDate || !dueTime) {
      return;
    }

    const current = new Date();
    const isToday =
      dueDate.getFullYear() === current.getFullYear() &&
      dueDate.getMonth() === current.getMonth() &&
      dueDate.getDate() === current.getDate();

    if (!isToday) {
      return;
    }

    const [hours, minutes] = dueTime.split(':').map(Number);
    if (Number.isNaN(hours) || Number.isNaN(minutes)) {
      return;
    }

    const candidate = new Date(dueDate);
    candidate.setHours(hours, minutes, 0, 0);

    if (candidate.getTime() <= current.getTime()) {
      setDueTime('');
    }
  }, [dueDate, dueTime]);

  const handleSubmit = async () => {
    if (!selectedTestId || !participantEmails.trim()) {
      setError('Please select a test and enter participant emails');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const emails = participantEmails
        .split(',')
        .map((email) => email.trim())
        .filter((email) => email.length > 0);

      if (emails.length === 0) {
        throw new Error('Please enter at least one valid email address');
      }

      let dueDateIso: string | undefined;
      if (dueDate) {
        const combined = new Date(dueDate);
        if (dueTime) {
          const [hoursPart, minutesPart] = dueTime.split(':');
          const hours = Number(hoursPart);
          const minutes = Number(minutesPart);

          if (Number.isNaN(hours) || Number.isNaN(minutes)) {
            throw new Error('Please choose a valid due time');
          }

          combined.setHours(hours, minutes, 0, 0);
        } else {
          combined.setHours(23, 59, 59, 0);
        }

        if (combined.getTime() <= Date.now()) {
          throw new Error('Please choose a future due date and time');
        }

        dueDateIso = combined.toISOString();
      }

      await bulkAssignTest({
        test_id: parseInt(selectedTestId, 10),
        participant_emails: emails,
        assigned_by: 'current_user',
        due_date: dueDateIso,
      });

      const participantCount = emails.length;
      toast.success('Test assigned successfully!', {
        description: `${selectedTest?.name || 'Test'} has been assigned to ${participantCount} participant${participantCount > 1 ? 's' : ''}.`,
      });

      setSelectedTestId(defaultTestId ? `${defaultTestId}` : '');
      setParticipantEmails('');
      setDueDate(undefined);
      setDueTime('');
      setDatePickerOpen(false);
      setOpen(false);

      onSuccess?.();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to assign test';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const selectedTest = options.find((test) => test.id.toString() === selectedTestId);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          className={cn('justify-start transition-transform hover:-translate-y-0.5', triggerClassName ?? 'w-full')}
          variant="outline"
        >
          Assign Tests to Students
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>Assign Test to Students</DialogTitle>
          <DialogDescription>
            Select a test and enter participant email addresses to assign the assessment.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          {!hideTestSelection && (
            <div className="grid gap-2">
              <Label htmlFor="test-select">Select Test</Label>
              <Select value={selectedTestId} onValueChange={setSelectedTestId}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose a test to assign" />
                </SelectTrigger>
                <SelectContent>
                  {options.map((test) => (
                    <SelectItem key={test.id} value={test.id.toString()}>
                      {test.name} ({getFriendlyType(test.test_type)})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {selectedTest && (
            <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
              <p className="font-medium">{selectedTest.name}</p>
              <p>Type: {getFriendlyType(selectedTest.test_type)}</p>
              <p>
                Duration:{' '}
                {selectedTest.duration_seconds ? `${Math.round(selectedTest.duration_seconds / 60)} minutes` : 'No limit'}
              </p>
              <p>Status: {selectedTest.active ? 'Active' : 'Inactive'}</p>
            </div>
          )}

          <div className="grid gap-2">
            <Label htmlFor="emails">Participant Emails</Label>
            <Textarea
              id="emails"
              placeholder="Enter email addresses separated by commas&#10;example@company.com, student@company.com"
              value={participantEmails}
              onChange={(e) => setParticipantEmails(e.target.value)}
              rows={4}
            />
            <p className="text-xs text-slate-500">Separate multiple email addresses with commas</p>
          </div>

          <div className="grid gap-3">
            <Label className="px-1 text-sm font-medium text-slate-600">Due Date (Optional)</Label>
            <div className="flex flex-wrap items-end gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="date-picker" className="px-1 text-sm text-slate-600">
                  Date
                </Label>
                <Popover open={datePickerOpen} onOpenChange={setDatePickerOpen}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      id="date-picker"
                      className="w-36 justify-between font-normal"
                    >
                      {dueDate ? formatTableDate(dueDate).split(',')[0] : 'Select date'}
                      <ChevronDownIcon className="size-4" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto overflow-hidden p-0" align="start">
                    <Calendar
                      mode="single"
                      selected={dueDate}
                      captionLayout="dropdown"
                      disabled={(date) => date < startOfToday}
                      onSelect={(value) => {
                        setDueDate(value || undefined);
                        if (!value) {
                          setDueTime('');
                        } else {
                          setDatePickerOpen(false);
                        }
                      }}
                    />
                  </PopoverContent>
                </Popover>
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="time-picker" className="px-1 text-sm text-slate-600">
                  Time
                </Label>
                <Input
                  type="time"
                  id="time-picker"
                  step={60}
                  min={isDueDateToday ? minSelectableTime : undefined}
                  value={dueTime}
                  onChange={(event) => setDueTime(event.target.value)}
                  disabled={!dueDate}
                  className="w-32 bg-background appearance-none disabled:cursor-not-allowed [&::-webkit-calendar-picker-indicator]:hidden [&::-webkit-calendar-picker-indicator]:appearance-none"
                />
              </div>
            </div>
          </div>

          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading ? 'Assigning…' : 'Assign Test'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
