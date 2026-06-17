'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from 'recharts';
import type { UserSessionEntry } from '@/lib/api/types';

interface ResultsChartProps {
  attempts: UserSessionEntry[];
  currentSessionId?: string;
}

interface ChartEntry {
  label: string;
  score: number;
  passed: boolean;
  isCurrent: boolean;
  completedAt?: string;
}

const PASS_COLOR = '#22c55e';
const FAIL_COLOR = '#ef4444';
const CURRENT_PASS_COLOR = '#15803d';
const CURRENT_FAIL_COLOR = '#b91c1c';

export default function ResultsChart({ attempts, currentSessionId }: ResultsChartProps) {
  const ordered = [...attempts].reverse();

  const data: ChartEntry[] = ordered.map((a, i) => ({
    label: `#${i + 1}`,
    score: Math.round(a.percentage_score ?? 0),
    passed: (a.percentage_score ?? 0) >= 70,
    isCurrent: a.session_id === currentSessionId,
    completedAt: a.completed_at,
  }));

  if (data.length === 0) {
    return (
      <p className="text-sm text-slate-500 text-center py-8">
        No attempt data available.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={240} aria-label="Score per attempt colored by pass or fail">
      <BarChart
        data={data}
        margin={{ top: 4, right: 8, bottom: 4, left: 0 }}
        barCategoryGap="20%"
      >
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          domain={[0, 100]}
          tickFormatter={(v) => `${v}%`}
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={40}
        />
        <Tooltip
          formatter={(value: number) => [`${value}%`, 'Score']}
          labelFormatter={(label) => `Attempt ${label}`}
        />
        <Bar dataKey="score" radius={[4, 4, 0, 0]}>
          {data.map((entry, index) => (
            <Cell
              key={index}
              fill={
                entry.isCurrent
                  ? entry.passed ? CURRENT_PASS_COLOR : CURRENT_FAIL_COLOR
                  : entry.passed ? PASS_COLOR : FAIL_COLOR
              }
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
