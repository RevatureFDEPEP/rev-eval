'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import * as z from 'zod';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { NumberInput } from '@/components/ui/number-input';
import { Separator } from '@/components/ui/separator';
import { ArrowLeft, BookOpen, Clock, X } from 'lucide-react';
import Link from 'next/link';
import { createTest, getSkills, getTest } from '@/lib/api';
import type { SkillInfo } from '@/lib/api/types';
import { TestType } from '@/lib/api/types';
import { toast } from 'sonner';

// Form validation schema
const testFormSchema = z.object({
  name: z.string().min(3, 'Test name must be at least 3 characters'),
  role: z.string().min(1, 'Role is required'),
  duration_minutes: z.number().min(5, 'Minimum duration is 5 minutes').max(240, 'Maximum duration is 240 minutes'),
  number_of_questions: z.number().min(10, 'Minimum 10 questions').max(50, 'Maximum 50 questions'),
  active: z.boolean(),
  skill_ids: z.array(z.number()).min(1, 'Select at least one skill'),
});

type TestFormValues = z.infer<typeof testFormSchema>;

export default function CreateTestPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const typeParam = searchParams.get('type');
  const cloneParam = searchParams.get('clone');
  const resolvedType = (typeParam || 'QUIZ').toUpperCase();
  const initialTestType = (resolvedType === 'INTERVIEW' ? 'INTERVIEW' : 'QUIZ') as 'QUIZ' | 'INTERVIEW';
  const parsedCloneId = cloneParam ? Number.parseInt(cloneParam, 10) : NaN;
  const cloneId = Number.isNaN(parsedCloneId) ? null : parsedCloneId;

  const [testType, setTestType] = useState<'QUIZ' | 'INTERVIEW'>(initialTestType);
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [prefilling, setPrefilling] = useState(Boolean(cloneId));
  const [clonedFrom, setClonedFrom] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const form = useForm<TestFormValues>({
    resolver: zodResolver(testFormSchema),
    defaultValues: {
      name: '',
      role: '',
      duration_minutes: initialTestType === 'QUIZ' ? 45 : 30,
      number_of_questions: 20,
      active: true,
      skill_ids: [],
    },
  });

  // Load skills on mount
  useEffect(() => {
    const loadSkills = async () => {
      try {
        setLoading(true);
        const skillsData = await getSkills();
        setSkills(skillsData);
      } catch (err) {
        console.error('Error loading skills:', err);
        setError('Failed to load skills. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    loadSkills();
  }, []);

  useEffect(() => {
    if (!cloneId) {
      setClonedFrom(null);
      setPrefilling(false);
      return;
    }

    let isMounted = true;

    const prefillFromClone = async () => {
      try {
        setPrefilling(true);
        const clone = await getTest(cloneId);
        if (!isMounted || !clone) return;

        const derivedType = (clone.test_type as string) === 'INTERVIEW' ? 'INTERVIEW' : 'QUIZ';
        const derivedSkillIds = Array.isArray(clone.skill_ids) && clone.skill_ids.length
          ? clone.skill_ids
          : (clone.skills ?? []).map((skill) => skill.id);
        const uniqueSkillIds = Array.from(new Set(derivedSkillIds));

        const derivedDuration = clone.duration_seconds
          ? Math.max(5, Math.round(clone.duration_seconds / 60))
          : derivedType === 'INTERVIEW'
            ? 30
            : 45;

        form.reset({
          name: `${clone.name} (1)`,
          role: clone.role || '',
          duration_minutes: derivedDuration,
          number_of_questions: clone.number_of_questions || 20,
          active: clone.active ?? true,
          skill_ids: uniqueSkillIds,
        });

        setTestType(derivedType);
        setClonedFrom(clone.name);
      } catch (err) {
        console.error('Error loading test for cloning:', err);
        setClonedFrom(null);
        setError('Unable to preload details from the selected test. You can still configure a new one below.');
      } finally {
        if (isMounted) {
          setPrefilling(false);
        }
      }
    };

    prefillFromClone();

    return () => {
      isMounted = false;
    };
  }, [cloneId, form, setTestType, setClonedFrom, setPrefilling, setError]);

  const onSubmit = async (values: TestFormValues) => {
    try {
      setSubmitting(true);
      setError(null);

      // Convert duration to seconds
      const testData = {
        name: values.name,
        test_type: testType === 'QUIZ' ? TestType.QUIZ : TestType.INTERVIEW,
        role: values.role,
        duration_seconds: values.duration_minutes * 60,
        number_of_questions: values.number_of_questions,
        active: values.active,
        skill_ids: values.skill_ids,
      };

      await createTest(testData);

      toast.success('Test created successfully!', {
        description: `"${values.name}" is now available to assign.`,
      });

      // Redirect to tests page
      router.push('/trainer/tests');
    } catch (err) {
      console.error('Error creating test:', err);
      setError(err instanceof Error ? err.message : 'Failed to create test');
    } finally {
      setSubmitting(false);
    }
  };

  const filteredSkills = skills.filter((skill) =>
    skill.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const selectedSkillIds = form.watch('skill_ids') ?? [];
  const selectedSkills = selectedSkillIds
    .map((id) => skills.find((skill) => skill.id === id))
    .filter((skill): skill is SkillInfo => Boolean(skill));

  const skillListContainerClass =
    'max-h-[55vh] overflow-x-hidden overflow-y-auto overscroll-contain rounded-lg border border-slate-200 bg-white';

  const isQuiz = testType === 'QUIZ';

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            <span>Trainer workspace</span>
            <span className="h-1 w-1 rounded-full bg-slate-300" />
            <Link href="/trainer/tests" className="hover:text-slate-700">Tests</Link>
            <span className="h-1 w-1 rounded-full bg-slate-300" />
            <span className="text-slate-400">Create {isQuiz ? 'Quiz' : 'Interview'}</span>
          </div>
          <h1 className="text-3xl font-semibold text-slate-900">Create New {isQuiz ? 'Quiz' : 'Interview'} Test</h1>
          <p className="max-w-2xl text-sm text-slate-500">
            Configure the assessment details and select skills to evaluate
          </p>
          {prefilling && !clonedFrom && (
            <p className="text-xs text-slate-500">Loading defaults from the selected test…</p>
          )}
          {clonedFrom && (
            <p className="text-xs text-slate-500">
              Prefilled from &ldquo;{clonedFrom}&rdquo;
            </p>
          )}
        </div>
        <Badge variant="secondary" className="rounded-full px-4 py-1 text-xs font-semibold">
          Trainer
        </Badge>
      </section>

      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <p className="text-sm text-red-800">
              <strong>Error:</strong> {error}
            </p>
          </CardContent>
        </Card>
      )}

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            {/* Basic Information Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BookOpen className="size-5 text-orange-400" />
                  Basic Information
                </CardTitle>
                <CardDescription>General details about the test</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Test Name</FormLabel>
                      <FormControl>
                        <Input placeholder="e.g., Java Fundamentals Quiz" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="role"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Target Role</FormLabel>
                      <FormControl>
                        <Input placeholder="e.g., Java Developer" {...field} />
                      </FormControl>
                      <FormDescription>The job role this test is designed for</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="active"
                  render={({ field }) => (
                    <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                      <FormControl>
                        <Checkbox checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                      <div className="space-y-1 leading-none">
                        <FormLabel>Active</FormLabel>
                        <FormDescription>Make this test available for assignment immediately</FormDescription>
                      </div>
                    </FormItem>
                  )}
                />
              </CardContent>
            </Card>

            {/* Configuration Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="size-5 text-purple-400" />
                  Configuration
                </CardTitle>
                <CardDescription>Test settings and duration</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <FormField
                  control={form.control}
                  name="duration_minutes"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Duration (minutes)</FormLabel>
                      <FormControl>
                        <NumberInput
                          min={5}
                          max={240}
                          step={5}
                          value={field.value}
                          onChange={field.onChange}
                        />
                      </FormControl>
                      <FormDescription>Time limit for completing the test (5-240 minutes)</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="number_of_questions"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Number of Questions</FormLabel>
                      <FormControl>
                        <NumberInput
                          min={10}
                          max={50}
                          step={1}
                          value={field.value}
                          onChange={field.onChange}
                        />
                      </FormControl>
                      <FormDescription>Total questions for the quiz (Part A + Part B). Default: 20</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className="rounded-md border p-4">
                  <div className="mb-2 text-sm font-medium">Test Type</div>
                  <Badge variant={isQuiz ? 'default' : 'secondary'}>{isQuiz ? 'Quiz' : 'Interview'}</Badge>
                  <p className="mt-2 text-xs text-slate-500">
                    {isQuiz
                      ? 'Multiple choice questions with automated scoring'
                      : 'AI-powered voice interview with conversation-based assessment'}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Skills Selection Card */}
          <Card>
            <CardHeader>
              <CardTitle>Skills Assessment</CardTitle>
              <CardDescription>
                Select the skills this test will evaluate (selected {selectedSkillIds.length} skills)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="skill_ids"
                render={() => (
                  <FormItem>
                    <div className="mb-4">
                      <Input
                        placeholder="Search skills..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="max-w-md"
                      />
                    </div>

                    {selectedSkills.length > 0 && (
                      <div className="mb-4 flex flex-wrap gap-2">
                        {selectedSkills.map((skill) => (
                          <Badge
                            key={skill.id}
                            variant="secondary"
                            className="flex items-center gap-2 rounded-full px-3 py-1 text-xs"
                          >
                            <span>{skill.name}</span>
                            <button
                              type="button"
                              disabled={prefilling}
                              onClick={() =>
                                form.setValue(
                                  'skill_ids',
                                  selectedSkillIds.filter((id) => id !== skill.id),
                                  { shouldValidate: true, shouldDirty: true }
                                )
                              }
                              className="rounded-full p-1 text-orange-500 transition hover:bg-white/60 hover:text-orange-600 disabled:opacity-50 disabled:hover:bg-transparent"
                              aria-label={`Remove ${skill.name}`}
                            >
                              <X className="size-3" />
                            </button>
                          </Badge>
                        ))}
                      </div>
                    )}

                    {loading ? (
                      <div className="flex h-48 items-center justify-center rounded-lg border border-dashed bg-slate-50">
                        <div className="text-center">
                          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-b-2 border-slate-900" />
                          <p className="mt-2 text-sm text-slate-600">Loading skills...</p>
                        </div>
                      </div>
                    ) : filteredSkills.length === 0 ? (
                      <div className="rounded-lg border border-dashed bg-white p-6 text-center text-sm text-slate-500">
                        No skills match your search.
                      </div>
                    ) : (
                      <div className={skillListContainerClass}>
                        <div className="grid gap-2 p-4 sm:grid-cols-2 lg:grid-cols-3">
                          {filteredSkills.map((skill) => (
                            <FormField
                              key={skill.id}
                              control={form.control}
                              name="skill_ids"
                              render={({ field }) => {
                                return (
                                  <FormItem
                                    key={skill.id}
                                    className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-3 hover:bg-muted/50"
                                  >
                                    <FormControl>
                                      <Checkbox
                                        checked={field.value?.includes(skill.id)}
                                        disabled={loading || prefilling}
                                        onCheckedChange={(checked) => {
                                          return checked
                                            ? field.onChange([...field.value, skill.id])
                                            : field.onChange(field.value?.filter((value) => value !== skill.id));
                                        }}
                                      />
                                    </FormControl>
                                    <FormLabel className="cursor-pointer text-sm font-normal">
                                      {skill.name}
                                    </FormLabel>
                                  </FormItem>
                                );
                              }}
                            />
                          ))}
                        </div>
                      </div>
                    )}
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <Separator />

          {/* Action Buttons */}
          <div className="flex items-center justify-between">
            <Button type="button" variant="outline" asChild>
              <Link href="/trainer/tests">
                <ArrowLeft className="mr-2 size-4" />
                Cancel
              </Link>
            </Button>
            <Button type="submit" disabled={submitting || prefilling}>
              {submitting
                ? 'Creating...'
                : prefilling
                  ? 'Loading defaults...'
                  : `Create ${isQuiz ? 'Quiz' : 'Interview'} Test`}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
