"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import { ApiError, browserTimezone } from "@/lib/api";
import { ERROR_HINTS } from "@/lib/format";
import { useCreateAnalysis } from "@/lib/queries";
import { analyzeSchema, type AnalyzeInput } from "@/lib/validation";

const schema = analyzeSchema;
type FormValues = AnalyzeInput;

export function AnalyzeForm() {
  const router = useRouter();
  const create = useCreateAnalysis();
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
    try {
      const job = await create.mutateAsync({
        username: parsed.username,
        post_limit: parsed.post_limit,
        timezone: browserTimezone(),
      });
      router.push(`/analysis/${job.id}`);
    } catch {
      // Error surfaced below via create.error.
    }
  });

  const apiErr = create.error as ApiError | null;

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="flex-1">
          <input
            {...register("username")}
            placeholder="@username"
            aria-label="X username"
            aria-invalid={!!errors.username}
            className="w-full rounded-lg border border-base-600 bg-base-900 px-4 py-3 outline-none focus:border-accent"
          />
          {errors.username && (
            <p className="mt-1 text-sm text-red-400">{errors.username.message}</p>
          )}
        </div>
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
        <button
          type="submit"
          disabled={create.isPending}
          className="rounded-lg bg-accent px-6 py-3 font-medium text-base-900 hover:bg-accent-muted disabled:opacity-60"
        >
          {create.isPending ? "Starting…" : "Analyze Profile"}
        </button>
      </div>

      {apiErr && (
        <div className="rounded-lg border border-red-700/40 bg-red-900/20 px-4 py-3 text-sm text-red-200">
          {ERROR_HINTS[apiErr.code] || apiErr.message}
        </div>
      )}

      <p className="text-xs text-gray-500">
        Demo mode is active by default. Try <code>protected_demo</code>,{" "}
        <code>empty_demo</code>, or <code>news_bot</code> to see how different
        cases are handled.
      </p>
    </form>
  );
}
