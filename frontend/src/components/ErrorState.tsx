"use client";

import Link from "next/link";

import { ERROR_HINTS } from "@/lib/format";

const ICONS: Record<string, string> = {
  PROFILE_NOT_FOUND: "🔍",
  PROFILE_PROTECTED: "🔒",
  PROFILE_SUSPENDED: "🚫",
  NO_POSTS_AVAILABLE: "📭",
  CREDENTIALS_MISSING: "🔑",
  RATE_LIMITED: "⏳",
  UNSUPPORTED_LANGUAGE: "🌐",
  NETWORK_ERROR: "📡",
  ANALYSIS_FAILED: "⚠️",
};

export function ErrorState({
  code,
  message,
  onRetry,
}: {
  code: string | null;
  message?: string | null;
  onRetry?: () => void;
}) {
  const key = code || "ANALYSIS_FAILED";
  const hint = ERROR_HINTS[key] || message || "Something went wrong.";
  return (
    <div className="mx-auto max-w-lg rounded-xl border border-base-700 bg-base-800 p-8 text-center">
      <div className="text-4xl" aria-hidden>
        {ICONS[key] || "⚠️"}
      </div>
      <h2 className="mt-3 text-lg font-medium text-gray-100">
        {key.replaceAll("_", " ").toLowerCase().replace(/^\w/, (c) => c.toUpperCase())}
      </h2>
      <p className="mt-2 text-sm text-gray-400">{hint}</p>
      <div className="mt-5 flex justify-center gap-3">
        {onRetry && (
          <button
            onClick={onRetry}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-base-900 hover:bg-accent-muted"
          >
            Try again
          </button>
        )}
        <Link
          href="/"
          className="rounded-lg border border-base-600 px-4 py-2 text-sm text-gray-200 hover:border-accent"
        >
          New analysis
        </Link>
      </div>
    </div>
  );
}
