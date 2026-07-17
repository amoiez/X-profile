import type { ReactNode } from "react";

export function Card({
  title,
  subtitle,
  children,
  className = "",
  action,
}: {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
  action?: ReactNode;
}) {
  return (
    <section
      className={`rounded-xl border border-base-700 bg-base-800 p-5 ${className}`}
    >
      {(title || action) && (
        <div className="mb-3 flex items-start justify-between gap-2">
          <div>
            {title && <h3 className="font-medium text-gray-100">{title}</h3>}
            {subtitle && <p className="text-xs text-gray-400">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
}) {
  return (
    <div className="rounded-lg border border-base-700 bg-base-800 p-4">
      <div className="text-xs uppercase tracking-wide text-gray-400">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-gray-100">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-gray-500">{hint}</div>}
    </div>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "positive" | "warning" | "danger" | "accent";
}) {
  const tones: Record<string, string> = {
    neutral: "bg-base-700 text-gray-300",
    positive: "bg-emerald-900/40 text-emerald-300 border border-emerald-700/40",
    warning: "bg-yellow-900/30 text-yellow-200 border border-yellow-700/40",
    danger: "bg-red-900/30 text-red-300 border border-red-700/40",
    accent: "bg-sky-900/30 text-sky-300 border border-sky-700/40",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center rounded-lg border border-dashed border-base-600 p-6 text-sm text-gray-500">
      {message}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-gray-300">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-base-600 border-t-accent" />
      {label && <span className="text-sm">{label}</span>}
    </div>
  );
}
