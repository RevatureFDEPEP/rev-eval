'use client';

import React, { useEffect, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { getAggregateReport, type TestAggregateSummary } from '@/lib/api/reports';

function truncate(name: string, max = 18): string {
  return name.length > max ? `${name.slice(0, max)}…` : name;
}

interface ChartDataPoint {
  name: string;
  attempts: number;
  avg: number;
  pass_rate: number;
}

interface ChartWrapperProps {
  title: string;
  description: string;
  data: ChartDataPoint[];
  children: React.ReactNode;
}

function ChartWrapper({ title, description, data, children }: ChartWrapperProps) {
  return (
    <Card className="border border-slate-200/70 bg-white/95 shadow-sm">
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data} margin={{ top: 4, right: 8, left: -10, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11 }}
              angle={-30}
              textAnchor="end"
              interval={0}
            />
            {children}
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export function AggregateCharts() {
  const [data, setData] = useState<TestAggregateSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAggregateReport()
      .then((res) => setData(res.tests))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-slate-500">
        Loading analytics…
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800">
        {error}
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-slate-500">
        No completed attempts yet.
      </div>
    );
  }

  const chartData = data.map((t) => ({
    name: truncate(t.test_name),
    attempts: t.attempt_count,
    avg: t.avg_score !== null ? Math.round(t.avg_score) : 0,
    pass_rate: t.pass_rate !== null ? Math.round(t.pass_rate * 100) : 0,
  }));

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <ChartWrapper title="Attempts per Test" description="Total completed attempts" data={chartData}>
        <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
        <Tooltip />
        <Bar dataKey="attempts" radius={[4, 4, 0, 0]}>
          {chartData.map((_, i) => (
            <Cell key={i} fill={i % 2 === 0 ? '#f97316' : '#c2410c'} />
          ))}
        </Bar>
      </ChartWrapper>

      <ChartWrapper title="Pass Rate % per Test" description=">= 70% threshold" data={chartData}>
        <YAxis tick={{ fontSize: 11 }} domain={[0, 100]} unit="%" />
        <Tooltip formatter={(v) => `${v}%`} />
        <Bar dataKey="pass_rate" radius={[4, 4, 0, 0]}>
          {chartData.map((entry, i) => (
            <Cell key={i} fill={entry.pass_rate >= 50 ? '#22c55e' : '#f97316'} />
          ))}
        </Bar>
      </ChartWrapper>
    </div>
  );
}
