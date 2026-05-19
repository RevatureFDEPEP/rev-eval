'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
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
import { updateTest, getSkills, getTest, getCurrentUser } from '@/lib/api';
import type { SkillInfo } from '@/lib/api';
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

export default function EditTestPage() {
  const router = useRouter();
  const params = useParams();
  const testId = Number(params.testId);

  const [testType, setTestType] = useState<'QUIZ' | 'INTERVIEW'>('QUIZ');
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [permissionError, setPermissionError] = useState(false);

  const form = useForm<TestFormValues>({
    resolver: zodResolver(testFormSchema),
    defaultValues: {
      name: '',
      role: '',
      duration_minutes: 45,
      number_of_questions: 20,
      active: true,
      skill_ids: [],
    },
  });

  // Load current user and check permissions
  useEffect(() => {
    const loadUserAndTest = async () => {
      try {
        setLoading(true);

        // Load current user
        const user = await getCurrentUser();

        // Load test
        const testData = await getTest(testId);

        // Check permission - user must be the creator
        // Note: created_by_id might be null for old tests created before user tracking was implemented
        const creatorId = testData.created_by_id;
        if (creatorId != null && Number(creatorId) !== Number(user.id)) {
          setPermissionError(true);
          setError('You do not have permission to edit this test. Only the creator can edit it.');
          return;
        }
        // If created_by_id is null, allow editing (legacy tests)

        // Load skills
        const skillsData = await getSkills();
        setSkills(skillsData);

        // Set form values
        const derivedType = (testData.test_type as string) === 'INTERVIEW' ? 'INTERVIEW' : 'QUIZ';
        const derivedSkillIds = Array.isArray(testData.skill_ids) && testData.skill_ids.length
          ? testData.skill_ids
          : (testData.skills ?? []).map((skill) => skill.id);
        const uniqueSkillIds = Array.from(new Set(derivedSkillIds));

        const derivedDuration = testData.duration_seconds
          ? Math.max(5, Math.round(testData.duration_seconds / 60))
          : derivedType === 'INTERVIEW'
            ? 30
            : 45;

        form.reset({
          name: testData.name,
          role: testData.role || '',
          duration_minutes: derivedDuration,
          number_of_questions: testData.number_of_questions || 20,
          active: testData.active ?? true,
          skill_ids: uniqueSkillIds,
        });

        setTestType(derivedType);
      } catch (err) {
        console.error('Error loading test:', err);
        setError('Failed to load test. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    if (testId) {
      loadUserAndTest();
    }
  }, [testId, form]);

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

      await updateTest(testId, testData);

      toast.success('Test updated successfully!', {
        description: `"${values.name}" has been updated.`,
      });

      // Redirect to tests page
      router.push('/trainer/tests');
    } catch (err) {
      console.error('Error updating test:', err);
      setError(err instanceof Error ? err.message : 'Failed to update test');
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

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-b-2 border-slate-900" />
          <p className="mt-4 text-sm text-slate-600">Loading test...</p>
        </div>
      </div>
    );
  }

  if (permissionError) {
    return (
      <div className="space-y-6">
        <section className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <h1 className="text-3xl font-semibold text-slate-900">Permission Denied</h1>
            <p className="max-w-2xl text-sm text-slate-500">
              You do not have permission to edit this test.
            </p>
          </div>
        </section>

        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <p className="text-sm text-red-800">
              <strong>Error:</strong> {error}
            </p>
          </CardContent>
        </Card>

        <Button variant="outline" asChild>
          <Link href="/trainer/tests">
            <ArrowLeft className="mr-2 size-4" />
            Back to Tests
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            <span>Trainer workspace</span>
            <span className="h-1 w-1 rounded-full bg-slate-300" />
            <Link href="/trainer/tests" className="hover:text-slate-700">Tests</Link>
            <span className="h-1 w-1 rounded-full bg-slate-300" />
            <span className="text-slate-400">Edit {isQuiz ? 'Quiz' : 'Interview'}</span>
          </div>
          <h1 className="text-3xl font-semibold text-slate-900">Edit {isQuiz ? 'Quiz' : 'Interview'} Test</h1>
          <p className="max-w-2xl text-sm text-slate-500">
            Update the assessment details and modify skills to evaluate
          </p>
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
                              onClick={() =>
                                form.setValue(
                                  'skill_ids',
                                  selectedSkillIds.filter((id) => id !== skill.id),
                                  { shouldValidate: true, shouldDirty: true }
                                )
                              }
                              className="rounded-full p-1 text-orange-500 transition hover:bg-white/60 hover:text-orange-600"
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
                                        disabled={loading}
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
            <Button type="submit" disabled={submitting}>
              {submitting ? 'Updating...' : 'Update Test'}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
