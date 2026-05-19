"use client";

import { useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, LineChart, Line } from 'recharts';
import { TrainerTestInfo } from '@/lib/api/types';

interface TrainerChartsProps {
  stats: {
    quiz_tests_count: number;
    interview_tests_count: number;
  };
  tests: TrainerTestInfo[];
}

export function TrainerCharts({ stats, tests }: TrainerChartsProps) {
  const testTypeData = [
    { name: 'Quiz Tests', value: stats.quiz_tests_count, color: '#fb923c' },
    { name: 'Interview Tests', value: stats.interview_tests_count, color: '#a855f7' },
  ];

  // Generate last 10 days data from created_at timestamps
  const last10DaysData = useMemo(() => {
    const today = new Date();
    const days = [];

    for (let i = 9; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      date.setHours(0, 0, 0, 0);

      const nextDate = new Date(date);
      nextDate.setDate(nextDate.getDate() + 1);

      const testsCreated = tests.filter(test => {
        const createdDate = new Date(test.created_at);
        return createdDate >= date && createdDate < nextDate;
      }).length;

      const assignmentsGiven = tests.reduce((sum, test) => {
        const createdDate = new Date(test.created_at);
        if (createdDate >= date && createdDate < nextDate) {
          return sum + test.total_submissions;
        }
        return sum;
      }, 0);

      days.push({
        day: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        created: testsCreated,
        assigned: assignmentsGiven,
      });
    }

    return days;
  }, [tests]);

  // Calculate completion rate over tests
  const completionRateData = useMemo(() => {
    return tests
      .filter(test => test.total_submissions > 0)
      .slice(-10)
      .map(test => ({
        name: test.name.length > 20 ? test.name.substring(0, 20) + '...' : test.name,
        completionRate: test.total_submissions > 0
          ? Math.round((test.completed_submissions / test.total_submissions) * 100)
          : 0,
        completed: test.completed_submissions,
        total: test.total_submissions,
      }));
  }, [tests]);

  const chartConfig = {
    created: {
      label: "Tests Created",
      color: "#fb923c",
    },
    assigned: {
      label: "Assignments Given",
      color: "#a855f7",
    },
    completionRate: {
      label: "Completion Rate",
      color: "#10b981",
    },
    quiz: {
      label: "Quiz",
      color: "#fb923c",
    },
    interview: {
      label: "Interview",
      color: "#a855f7",
    },
  };

  const hasTests = stats.quiz_tests_count + stats.interview_tests_count > 0;
  const hasActivityData = last10DaysData.some(d => d.created > 0 || d.assigned > 0);
  const hasCompletionData = completionRateData.length > 0;

  return (
    <>
      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Activity Over Last 10 Days</CardTitle>
            <CardDescription>Tests created and assignments given</CardDescription>
          </CardHeader>
          <CardContent>
            {hasActivityData ? (
              <ChartContainer config={chartConfig} className="min-h-[200px] w-full">
                <BarChart data={last10DaysData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="day" tick={{ fontSize: 12 }} />
                  <YAxis />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Bar dataKey="created" fill="var(--color-created)" />
                  <Bar dataKey="assigned" fill="var(--color-assigned)" />
                </BarChart>
              </ChartContainer>
            ) : (
              <div className="flex h-[200px] items-center justify-center text-center">
                <div className="space-y-2">
                  <p className="text-sm text-slate-600">No activity in the last 10 days</p>
                  <p className="text-xs text-slate-500">Create tests and assign them to see activity trends</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Test Type Distribution</CardTitle>
            <CardDescription>Quiz vs Interview tests</CardDescription>
          </CardHeader>
          <CardContent>
            {hasTests ? (
              <ChartContainer config={chartConfig} className="min-h-[200px] w-full">
                <PieChart>
                  <Pie
                    data={testTypeData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={({ name, value }) => `${name}: ${value}`}
                  >
                    {testTypeData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <ChartTooltip content={<ChartTooltipContent />} />
                </PieChart>
              </ChartContainer>
            ) : (
              <div className="flex h-[200px] items-center justify-center text-center">
                <div className="space-y-2">
                  <p className="text-sm text-slate-600">No tests created yet</p>
                  <p className="text-xs text-slate-500">Create your first test to see the distribution</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Test Completion Rates</CardTitle>
          <CardDescription>Completion percentage by test (last 10 tests with assignments)</CardDescription>
        </CardHeader>
        <CardContent>
          {hasCompletionData ? (
            <ChartContainer config={chartConfig} className="min-h-[200px] w-full">
              <LineChart data={completionRateData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-45} textAnchor="end" height={80} />
                <YAxis label={{ value: 'Completion %', angle: -90, position: 'insideLeft' }} />
                <ChartTooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="rounded-lg border bg-background p-2 shadow-sm">
                          <div className="grid gap-2">
                            <div className="font-medium">{data.name}</div>
                            <div className="text-xs text-muted-foreground">
                              {data.completed} / {data.total} completed ({data.completionRate}%)
                            </div>
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="completionRate"
                  stroke="var(--color-completionRate)"
                  strokeWidth={2}
                  dot={{ fill: "var(--color-completionRate)" }}
                />
              </LineChart>
            </ChartContainer>
          ) : (
            <div className="flex h-[200px] items-center justify-center text-center">
              <div className="space-y-2">
                <p className="text-sm text-slate-600">No completion data available</p>
                <p className="text-xs text-slate-500">Assign tests to participants to see completion rates</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}
