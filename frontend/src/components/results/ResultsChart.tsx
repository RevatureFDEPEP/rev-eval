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
import type { GradedQuizQuestion } from '@/lib/api/types';

interface ResultsChartProps {
  partA: GradedQuizQuestion[];
  partB: GradedQuizQuestion[];
}

interface ChartEntry {
  label: string;
  time: number;
  correct: boolean;
  part: 'A' | 'B';
}

const CORRECT_COLOR = '#22c55e';
const INCORRECT_COLOR = '#ef4444';

export default function ResultsChart({ partA, partB }: ResultsChartProps) {
  const data: ChartEntry[] = [
    ...partA.map((q, i) => ({
      label: `A${i + 1}`,
      time: Math.max(q.time_spent_seconds ?? 0, 1),
      correct: q.is_correct ?? false,
      part: 'A' as const,
    })),
    ...partB.map((q, i) => ({
      label: `B${i + 1}`,
      time: Math.max(q.time_spent_seconds ?? 0, 1),
      correct: q.is_correct ?? false,
      part: 'B' as const,
    })),
  ];

  if (data.length === 0) {
    return (
      <p className="text-sm text-slate-500 text-center py-8">
        No question-level data available.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={240} aria-label="Per-question time spent colored by correctness">
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
          tickFormatter={(v) => `${v}s`}
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={36}
        />
        <Tooltip
          formatter={(value: number) => [`${value}s`, 'Time spent']}
          labelFormatter={(label) => `Question ${label}`}
        />
        <Bar dataKey="time" radius={[4, 4, 0, 0]}>
          {data.map((entry, index) => (
            <Cell
              key={index}
              fill={entry.correct ? CORRECT_COLOR : INCORRECT_COLOR}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
