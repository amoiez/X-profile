"use client";

const STAGES: [string, string][] = [
  ["validating", "Validating username"],
  ["retrieving_profile", "Retrieving public profile"],
  ["retrieving_posts", "Retrieving posts"],
  ["activity", "Calculating activity metrics"],
  ["content", "Running content analysis"],
  ["sentiment", "Analyzing sentiment"],
  ["engagement", "Measuring engagement"],
  ["patterns", "Detecting patterns"],
  ["generating_report", "Generating report"],
];

const ORDER = STAGES.map((s) => s[0]);

export function ProgressView({
  username,
  progress,
  stage,
}: {
  username: string;
  progress: number;
  stage: string | null;
}) {
  const currentIndex = stage ? ORDER.indexOf(stage) : 0;

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="text-xl font-medium">
        Analyzing <span className="text-accent">@{username}</span>
      </h1>
      <p className="mt-1 text-sm text-gray-400">
        This usually takes a few seconds. You can leave this page open.
      </p>

      <div className="mt-5">
        <div className="flex justify-between text-xs text-gray-400">
          <span>{STAGES[Math.max(0, currentIndex)]?.[1] ?? "Working…"}</span>
          <span>{progress}%</span>
        </div>
        <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-base-700">
          <div
            className="h-full rounded-full bg-accent transition-all duration-500"
            style={{ width: `${progress}%` }}
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
      </div>

      <ol className="mt-6 space-y-2">
        {STAGES.map(([key, label], i) => {
          const done = i < currentIndex || progress >= 100;
          const active = i === currentIndex && progress < 100;
          return (
            <li key={key} className="flex items-center gap-3 text-sm">
              <span
                className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] ${
                  done
                    ? "bg-emerald-600 text-white"
                    : active
                      ? "bg-accent text-base-900"
                      : "bg-base-700 text-gray-500"
                }`}
              >
                {done ? "✓" : i + 1}
              </span>
              <span className={done || active ? "text-gray-200" : "text-gray-500"}>
                {label}
              </span>
              {active && (
                <span className="h-3 w-3 animate-spin rounded-full border-2 border-base-600 border-t-accent" />
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
