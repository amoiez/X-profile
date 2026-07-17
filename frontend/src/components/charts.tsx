"use client";

import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  PolarAngleAxis,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AXIS, GRID, SENTIMENT, SERIES, heatColor, scoreBand, scoreColor } from "@/lib/colors";
import { WEEKDAY_LABELS } from "@/lib/format";
import { EmptyState } from "@/components/ui";

const TOOLTIP_STYLE = {
  backgroundColor: "#0b0f19",
  border: "1px solid #243043",
  borderRadius: 8,
  color: "#e5e7eb",
  fontSize: 12,
};
const AXIS_PROPS = { stroke: AXIS, fontSize: 12, tickLine: false };

function hasData(arr: number[] | undefined): boolean {
  return !!arr && arr.some((v) => v > 0);
}

/** Weekly posting activity — magnitude by category (bar). */
export function WeeklyActivityChart({ data }: { data: number[] }) {
  if (!hasData(data)) return <EmptyState message="No weekly activity to show." />;
  const rows = WEEKDAY_LABELS.map((day, i) => ({ day, posts: data[i] ?? 0 }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
        <XAxis dataKey="day" {...AXIS_PROPS} />
        <YAxis allowDecimals={false} {...AXIS_PROPS} />
        <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: "#ffffff08" }} />
        <Bar dataKey="posts" fill={SERIES[0]} radius={[4, 4, 0, 0]} name="Posts" />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Hourly activity heatmap — sequential single-hue intensity strip (24 cells). */
export function HourlyHeatmap({ data }: { data: number[] }) {
  if (!hasData(data)) return <EmptyState message="No hourly activity to show." />;
  const max = Math.max(...data, 1);
  return (
    <div>
      <div
        className="grid gap-1"
        style={{ gridTemplateColumns: "repeat(12, minmax(0, 1fr))" }}
      >
        {data.map((count, hour) => (
          <div
            key={hour}
            title={`${String(hour).padStart(2, "0")}:00 — ${count} post(s)`}
            className="flex aspect-square items-center justify-center rounded text-[9px] text-gray-300"
            style={{ backgroundColor: heatColor(count / max) }}
          >
            {hour % 3 === 0 ? hour : ""}
          </div>
        ))}
      </div>
      <p className="mt-2 text-xs text-gray-500">
        Darker = more posts. Hour of day in the selected timezone.
      </p>
    </div>
  );
}

/** Sentiment distribution — doughnut with legend + labels (secondary encoding). */
export function SentimentDoughnut({
  distribution,
}: {
  distribution: { positive: number; neutral: number; negative: number };
}) {
  const rows = [
    { name: "Positive", value: distribution.positive, fill: SENTIMENT.positive },
    { name: "Neutral", value: distribution.neutral, fill: SENTIMENT.neutral },
    { name: "Negative", value: distribution.negative, fill: SENTIMENT.negative },
  ];
  if (rows.every((r) => r.value === 0))
    return <EmptyState message="Sentiment unavailable for this sample." />;
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={rows}
          dataKey="value"
          nameKey="name"
          innerRadius={55}
          outerRadius={85}
          paddingAngle={2}
          label={(e) => `${e.name} ${Number(e.value).toFixed(0)}%`}
          labelLine={false}
          fontSize={11}
        >
          {rows.map((r) => (
            <Cell key={r.name} fill={r.fill} stroke="#0b0f19" strokeWidth={2} />
          ))}
        </Pie>
        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => `${v}%`} />
        <Legend wrapperStyle={{ fontSize: 12, color: "#9ca3af" }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

/** Top topics/keywords — horizontal magnitude bars. */
export function TopicsChart({
  data,
}: {
  data: { label: string; value: number }[];
}) {
  if (!data.length) return <EmptyState message="No topics detected." />;
  return (
    <ResponsiveContainer width="100%" height={Math.max(160, data.length * 34)}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
        <XAxis type="number" hide />
        <YAxis type="category" dataKey="label" width={110} {...AXIS_PROPS} />
        <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: "#ffffff08" }} />
        <Bar dataKey="value" fill={SERIES[0]} radius={[0, 4, 4, 0]} name="Count" />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Engagement by content type — magnitude bars. */
export function ContentTypeChart({
  data,
}: {
  data: { type: string; avg_engagement: number; count: number }[];
}) {
  if (!data.length) return <EmptyState message="No engagement data." />;
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -16 }}>
        <XAxis dataKey="type" {...AXIS_PROPS} />
        <YAxis {...AXIS_PROPS} />
        <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: "#ffffff08" }} />
        <Bar dataKey="avg_engagement" fill={SERIES[1]} radius={[4, 4, 0, 0]} name="Avg engagement" />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Sentiment trend over time — single line, change over time. */
export function SentimentTrendChart({
  data,
}: {
  data: { date: string; average: number }[];
}) {
  if (data.length < 2) return <EmptyState message="Not enough days for a trend." />;
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 8, right: 12, left: -16 }}>
        <XAxis dataKey="date" {...AXIS_PROPS} minTickGap={24} />
        <YAxis domain={[-1, 1]} {...AXIS_PROPS} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Line
          type="monotone"
          dataKey="average"
          stroke={SERIES[0]}
          strokeWidth={2}
          dot={{ r: 3 }}
          name="Avg sentiment"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

/** Automation-pattern score gauge (0–100), colored by band + explicit label. */
export function AutomationGauge({ score }: { score: number }) {
  const color = scoreColor(score);
  const rows = [{ name: "score", value: score, fill: color }];
  return (
    <div className="relative">
      <ResponsiveContainer width="100%" height={200}>
        <RadialBarChart
          innerRadius="72%"
          outerRadius="100%"
          data={rows}
          startAngle={210}
          endAngle={-30}
        >
          <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
          <RadialBar dataKey="value" cornerRadius={8} background={{ fill: GRID }} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <div className="text-4xl font-semibold" style={{ color }}>
          {score}
        </div>
        <div className="text-xs text-gray-400">/ 100 · {scoreBand(score)}</div>
      </div>
    </div>
  );
}
