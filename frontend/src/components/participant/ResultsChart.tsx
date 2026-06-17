'use client';

/**
 * ResultsChart — visualizes a single quiz attempt's outcome.
 *
 * Pure presentational component: it receives the already-fetched aggregate
 * score (no answer keys, no per-question correctness beyond the tally) and
 * renders a correct-vs-incorrect donut plus headline stats.
 */
import { Cell, Pie, PieChart } from 'recharts';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';

export interface ResultsChartProps {
  percentageScore: number;
  totalScore: number;
  maxScore: number;
  correctCount: number;
  answeredCount: number;
  totalQuestions: number;
}

const CORRECT_COLOR = '#10b981';
const INCORRECT_COLOR = '#ef4444';
const UNANSWERED_COLOR = '#cbd5e1';

export function ResultsChart({
  percentageScore,
  totalScore,
  maxScore,
  correctCount,
  answeredCount,
  totalQuestions,
}: ResultsChartProps) {
  const incorrect = Math.max(0, answeredCount - correctCount);
  const unanswered = Math.max(0, totalQuestions - answeredCount);

  const data = [
    { name: 'Correct', value: correctCount, color: CORRECT_COLOR },
    { name: 'Incorrect', value: incorrect, color: INCORRECT_COLOR },
    { name: 'Unanswered', value: unanswered, color: UNANSWERED_COLOR },
  ].filter((d) => d.value > 0);

  const chartConfig = {
    Correct: { label: 'Correct', color: CORRECT_COLOR },
    Incorrect: { label: 'Incorrect', color: INCORRECT_COLOR },
    Unanswered: { label: 'Unanswered', color: UNANSWERED_COLOR },
  };

  const rounded = Math.round(percentageScore);

  return (
    <div className="grid grid-cols-1 items-center gap-6 sm:grid-cols-2">
      <div className="relative mx-auto">
        <ChartContainer config={chartConfig} className="aspect-square h-[220px] w-[220px]">
          <PieChart>
            <ChartTooltip content={<ChartTooltipContent />} />
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={70}
              outerRadius={100}
              paddingAngle={2}
            >
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
          </PieChart>
        </ChartContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-4xl font-bold text-slate-900">{rounded}%</span>
          <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Score</span>
        </div>
      </div>

      <dl className="space-y-3 text-sm">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <dt className="text-slate-500">Points</dt>
          <dd className="font-semibold text-slate-900">
            {totalScore} / {maxScore}
          </dd>
        </div>
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <dt className="text-slate-500">Correct answers</dt>
          <dd className="font-semibold text-emerald-600">
            {correctCount} / {totalQuestions}
          </dd>
        </div>
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <dt className="text-slate-500">Incorrect</dt>
          <dd className="font-semibold text-red-600">{incorrect}</dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="text-slate-500">Unanswered</dt>
          <dd className="font-semibold text-slate-600">{unanswered}</dd>
        </div>
      </dl>
    </div>
  );
}
