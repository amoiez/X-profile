"use client";

import { AutomationGauge } from "@/components/charts";
import { Badge, Card } from "@/components/ui";
import { scoreColor } from "@/lib/colors";
import type { PatternMetrics } from "@/lib/types";

export function PatternPanel({ patterns }: { patterns: PatternMetrics }) {
  const score = patterns.automation_pattern_score;
  return (
    <Card
      title="Possible automation-pattern score"
      subtitle="Observable posting patterns only — not proof of automation."
    >
      <div className="grid gap-6 md:grid-cols-2">
        <div>
          <AutomationGauge score={score} />
          <div className="mt-3 flex flex-wrap gap-2">
            {patterns.signals_triggered.length ? (
              patterns.signals_triggered.map((s) => (
                <Badge key={s} tone="warning">
                  {s}
                </Badge>
              ))
            ) : (
              <Badge tone="positive">No strong signals</Badge>
            )}
          </div>
          <p className="mt-3 rounded-lg border border-base-700 bg-base-900 p-3 text-xs text-gray-400">
            {patterns.disclaimer}
          </p>
        </div>

        <div className="space-y-3">
          {patterns.components.map((c) => {
            const pct = c.max_points ? (c.points / c.max_points) * 100 : 0;
            return (
              <div key={c.key}>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-200">{c.label}</span>
                  <span className="text-gray-400">
                    {c.points.toFixed(1)} / {c.max_points}
                  </span>
                </div>
                <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-base-700">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${pct}%`, backgroundColor: scoreColor(score) }}
                  />
                </div>
                <p className="mt-1 text-xs text-gray-500">{c.explanation}</p>
              </div>
            );
          })}
        </div>
      </div>
    </Card>
  );
}
