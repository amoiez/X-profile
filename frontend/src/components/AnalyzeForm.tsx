"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { ApiError, browserTimezone } from "@/lib/api";
import { ERROR_HINTS } from "@/lib/format";
import { useCreateAnalysis, useCreateImportedAnalysis } from "@/lib/queries";
import { analyzeSchema, type AnalyzeInput } from "@/lib/validation";

const schema = analyzeSchema;
type FormValues = AnalyzeInput;
type Mode = "profile" | "csv";

const SAMPLE_CSV =
  "created_at,text,like_count,reply_count,repost_count,quote_count\n" +
  "2026-07-18T10:00:00Z,\"Building in public #ai\",12,3,4,1\n" +
  "2026-07-17T09:30:00Z,\"Another update @team\",8,1,2,0\n" +
  "2026-07-16T16:45:00Z,\"Quick thought about data quality\",21,4,5,2";

export function AnalyzeForm() {
  const router = useRouter();
  const create = useCreateAnalysis();
  const createImported = useCreateImportedAnalysis();
  const [mode, setMode] = useState<Mode>("profile");
  const [csvText, setCsvText] = useState("");
  const [csvError, setCsvError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { username: "", post_limit: 200 },
  });

  const onSubmit = handleSubmit(async (values) => {
    const parsed = schema.parse(values);
    const importedCsv = csvText.trim();
    setCsvError(null);

    if (mode === "csv" && !importedCsv) {
      setCsvError("Paste CSV data first, or use the sample CSV button.");
      return;
    }

    try {
      const job =
        mode === "csv"
          ? await createImported.mutateAsync({
              username: parsed.username,
              csv_text: importedCsv,
              timezone: browserTimezone(),
            })
          : await create.mutateAsync({
              username: parsed.username,
              post_limit: parsed.post_limit,
              timezone: browserTimezone(),
            });
      router.push(`/analysis/${job.id}`);
    } catch {
      // Error surfaced below via create.error / createImported.error.
    }
  });

  const apiErr = (createImported.error || create.error) as ApiError | null;
  const pending = create.isPending || createImported.isPending;
  const isCsv = mode === "csv";

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="inline-flex rounded-lg border border-base-600 bg-base-900 p-1 text-sm">
        <button
          type="button"
          onClick={() => setMode("profile")}
          className={`rounded-md px-3 py-1.5 ${
            !isCsv ? "bg-accent text-base-900" : "text-gray-300 hover:text-accent"
          }`}
        >
          Demo / live username
        </button>
        <button
          type="button"
          onClick={() => setMode("csv")}
          className={`rounded-md px-3 py-1.5 ${
            isCsv ? "bg-accent text-base-900" : "text-gray-300 hover:text-accent"
          }`}
        >
          Free CSV import
        </button>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="flex-1">
          <input
            {...register("username")}
            placeholder={isCsv ? "account_label" : "@username"}
            aria-label={isCsv ? "Account label" : "X username"}
            aria-invalid={!!errors.username}
            className="w-full rounded-lg border border-base-600 bg-base-900 px-4 py-3 outline-none focus:border-accent"
          />
          {errors.username && (
            <p className="mt-1 text-sm text-red-400">{errors.username.message}</p>
          )}
        </div>
        {!isCsv && (
          <div className="sm:w-40">
            <select
              {...register("post_limit")}
              aria-label="Number of posts"
              className="w-full rounded-lg border border-base-600 bg-base-900 px-4 py-3 outline-none focus:border-accent"
            >
              <option value={50}>50 posts</option>
              <option value={100}>100 posts</option>
              <option value={200}>200 posts</option>
              <option value={500}>500 posts</option>
            </select>
          </div>
        )}
        <button
          type="submit"
          disabled={pending}
          className="rounded-lg bg-accent px-6 py-3 font-medium text-base-900 hover:bg-accent-muted disabled:opacity-60"
        >
          {pending ? "Starting..." : isCsv ? "Analyze CSV" : "Analyze Profile"}
        </button>
      </div>

      {isCsv ? (
        <div>
          <div className="mb-2 flex items-center justify-between gap-3">
            <label htmlFor="csv-import" className="text-sm font-medium text-gray-200">
              Imported posts CSV
            </label>
            <button
              type="button"
              onClick={() => {
                setCsvText(SAMPLE_CSV);
                setCsvError(null);
              }}
              className="rounded-md border border-base-600 px-2.5 py-1 text-xs text-gray-300 hover:border-accent hover:text-accent"
            >
              Load sample CSV
            </button>
          </div>
          <textarea
            id="csv-import"
            value={csvText}
            onChange={(event) => {
              setCsvText(event.target.value);
              setCsvError(null);
            }}
            rows={7}
            placeholder="Paste CSV rows here. Required columns: created_at,text"
            aria-invalid={!!csvError}
            className="w-full rounded-lg border border-base-600 bg-base-900 px-4 py-3 font-mono text-sm outline-none focus:border-accent"
          />
          {csvError && <p className="mt-1 text-sm text-red-400">{csvError}</p>}
          <p className="mt-1 text-xs text-gray-500">
            Required columns: <code>created_at</code> and <code>text</code>.
            Optional: <code>like_count</code>, <code>reply_count</code>,{" "}
            <code>repost_count</code>, <code>quote_count</code>,{" "}
            <code>lang</code>, <code>hashtags</code>, <code>mentions</code>,{" "}
            <code>urls</code>.
          </p>
        </div>
      ) : (
        <p className="text-xs text-gray-500">
          Local demo mode accepts <code>sample_user</code>, <code>coffee_lover</code>,{" "}
          <code>news_bot</code>, <code>empty_demo</code>, <code>protected_demo</code>,{" "}
          and <code>suspended_demo</code>. Real live usernames require a configured
          X API bearer token.
        </p>
      )}

      {apiErr && (
        <div className="rounded-lg border border-red-700/40 bg-red-900/20 px-4 py-3 text-sm text-red-200">
          {ERROR_HINTS[apiErr.code] || apiErr.message}
        </div>
      )}
    </form>
  );
}
