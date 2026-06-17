'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ReferenceLine,
  Legend,
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
}

const PASS_COLOR = '#22c55e';
const FAIL_COLOR = '#ef4444';
const CURRENT_PASS_COLOR = '#15803d';
const CURRENT_FAIL_COLOR = '#b91c1c';

// session_id from the API is a numeric PK; currentSessionId comes from the
// URL param as a string. String() normalises both sides before comparison.
function isCurrent(attempt: UserSessionEntry, currentSessionId?: string): boolean {
  if (!currentSessionId) return false;
  return String(attempt.session_id) === currentSessionId;
}

export default function ResultsChart({ attempts, currentSessionId }: ResultsChartProps) {
  const ordered = [...attempts].reverse();

  const data: ChartEntry[] = ordered.map((a, i) => ({
    label: `#${i + 1}`,
    score: Math.round(a.percentage_score ?? 0),
    passed: (a.percentage_score ?? 0) >= 70,
    isCurrent: isCurrent(a, currentSessionId),
  }));

  if (data.length === 0) {
    return (
      <p className="text-sm text-slate-500 text-center py-8">
        No attempt data available.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280} aria-label="Score per attempt colored by pass or fail">
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
        <ReferenceLine
          y={70}
          stroke="#94a3b8"
          strokeDasharray="4 3"
          label={{ value: 'Pass (70%)', position: 'insideTopRight', fontSize: 10, fill: '#94a3b8' }}
        />
        <Tooltip
          formatter={(value: number) => [`${value}%`, 'Score']}
          labelFormatter={(label) => `Attempt ${label}`}
        />
        <Legend
          verticalAlign="bottom"
          height={28}
          formatter={(value) => value}
          payload={[
            { value: 'Passed', type: 'square', color: PASS_COLOR },
            { value: 'Failed', type: 'square', color: FAIL_COLOR },
            { value: 'This attempt', type: 'square', color: CURRENT_PASS_COLOR },
          ]}
        />
        <Bar dataKey="score" radius={[4, 4, 0, 0]} name="Score">
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
