"use client";

import { useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, LineChart, Line } from 'recharts';
import { TrendingUp, BarChart3 } from 'lucide-react';
import { AssignedTestInfo } from '@/lib/api/types';

interface AssociateChartsProps {
  stats: {
    assigned_tests_count: number;
    completed_tests_count: number;
    in_progress_tests_count: number;
    average_score?: number;
  };
  assignedTests: AssignedTestInfo[];
}

export function AssociateCharts({ stats, assignedTests }: AssociateChartsProps) {
  const completionData = [
    { name: 'Completed', value: stats.completed_tests_count, color: '#10b981' },
    { name: 'In Progress', value: stats.in_progress_tests_count, color: '#f59e0b' },
    { name: 'Assigned', value: stats.assigned_tests_count - stats.completed_tests_count - stats.in_progress_tests_count, color: '#6b7280' },
  ].filter(item => item.value > 0);

  // Generate last 10 days data from assigned and completed tests
  const last10DaysData = useMemo(() => {
    const today = new Date();
    const days = [];

    for (let i = 9; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      date.setHours(0, 0, 0, 0);

      const nextDate = new Date(date);
      nextDate.setDate(nextDate.getDate() + 1);

      const testsAssigned = assignedTests.filter(test => {
        const assignedDate = new Date(test.assigned_at);
        return assignedDate >= date && assignedDate < nextDate;
      }).length;

      const testsCompleted = assignedTests.filter(test => {
        if (!test.submitted_at) return false;
        const submittedDate = new Date(test.submitted_at);
        return submittedDate >= date && submittedDate < nextDate;
      }).length;

      days.push({
        day: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        assigned: testsAssigned,
        completed: testsCompleted,
      });
    }

    return days;
  }, [assignedTests]);

  // Calculate score trends from completed tests
  const scoreData = useMemo(() => {
    return assignedTests
      .filter(test => test.final_score != null && test.submitted_at)
      .sort((a, b) => new Date(a.submitted_at!).getTime() - new Date(b.submitted_at!).getTime())
      .slice(-10)
      .map(test => ({
        name: test.test_name.length > 20 ? test.test_name.substring(0, 20) + '...' : test.test_name,
        score: Math.round(test.final_score!),
        date: test.submitted_at,
      }));
  }, [assignedTests]);

  const chartConfig = {
    completed: {
      label: "Completed",
      color: "#10b981",
    },
    inProgress: {
      label: "In Progress",
      color: "#f59e0b",
    },
    assigned: {
      label: "Assigned",
      color: "#6b7280",
    },
    score: {
      label: "Score",
      color: "#10b981",
    },
  };

  const hasTests = stats.assigned_tests_count > 0;
  const hasActivityData = last10DaysData.some(d => d.assigned > 0 || d.completed > 0);
  const hasScoreData = scoreData.length > 0;

  return (
    <>
      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Activity Over Last 10 Days</CardTitle>
            <CardDescription>Tests assigned and completed</CardDescription>
          </CardHeader>
          <CardContent>
            {hasActivityData ? (
              <ChartContainer config={chartConfig} className="min-h-[200px] w-full">
                <BarChart data={last10DaysData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="day" tick={{ fontSize: 12 }} />
                  <YAxis />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Bar dataKey="assigned" fill="#6b7280" name="Assigned" />
                  <Bar dataKey="completed" fill="#10b981" name="Completed" />
                </BarChart>
              </ChartContainer>
            ) : (
              <div className="flex h-[200px] items-center justify-center text-center">
                <div className="space-y-2">
                  <p className="text-sm text-slate-600">No activity in the last 10 days</p>
                  <p className="text-xs text-slate-500">Tests will appear here once assigned by your trainer</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Test Completion</CardTitle>
            <CardDescription>Your test status overview</CardDescription>
          </CardHeader>
          <CardContent>
            {hasTests ? (
              <ChartContainer config={chartConfig} className="min-h-[200px] w-full">
                <PieChart>
                  <Pie
                    data={completionData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={({ name, value }) => `${name}: ${value}`}
                  >
                    {completionData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <ChartTooltip content={<ChartTooltipContent />} />
                </PieChart>
              </ChartContainer>
            ) : (
              <div className="flex h-[200px] items-center justify-center text-center">
                <div className="space-y-2">
                  <p className="text-sm text-slate-600">No tests assigned yet</p>
                  <p className="text-xs text-slate-500">Tests will appear here once assigned by your trainer</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Score Trends</CardTitle>
          <CardDescription>Your performance over time (last 10 completed tests)</CardDescription>
        </CardHeader>
        <CardContent>
          {hasScoreData ? (
            <ChartContainer config={chartConfig} className="min-h-[200px] w-full">
              <LineChart data={scoreData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-45} textAnchor="end" height={80} />
                <YAxis label={{ value: 'Score %', angle: -90, position: 'insideLeft' }} domain={[0, 100]} />
                <ChartTooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="rounded-lg border bg-background p-2 shadow-sm">
                          <div className="grid gap-2">
                            <div className="font-medium">{data.name}</div>
                            <div className="text-xs text-muted-foreground">
                              Score: {data.score}%
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {data.date ? new Date(data.date).toLocaleDateString() : 'Recently'}
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
                  dataKey="score"
                  stroke="var(--color-score)"
                  strokeWidth={2}
                  dot={{ fill: "var(--color-score)" }}
                />
              </LineChart>
            </ChartContainer>
          ) : (
            <div className="flex h-[200px] items-center justify-center text-center">
              <div className="space-y-2">
                <p className="text-sm text-slate-600">No completed tests yet</p>
                <p className="text-xs text-slate-500">Your score trends will appear here after completing tests</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}
