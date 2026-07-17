"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge, Card, EmptyState, Spinner } from "@/components/ui";
import { formatDate } from "@/lib/format";
import { useDeleteAnalysis, useHistory, useRefreshAnalysis } from "@/lib/queries";
import { useRouter } from "next/navigation";
import type { JobStatus } from "@/lib/types";

const STATUS_TONE: Record<JobStatus, "neutral" | "positive" | "warning" | "danger" | "accent"> = {
  completed: "positive",
  failed: "danger",
  running: "accent",
  pending: "warning",
};

export default function HistoryPage() {
  const [page, setPage] = useState(1);
  const { data, isLoading, isError } = useHistory(page);
  const del = useDeleteAnalysis();
  const refresh = useRefreshAnalysis();
  const router = useRouter();

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner label="Loading history…" />
      </div>
    );
  }
  if (isError) {
    return <EmptyState message="Could not load history." />;
  }

  const items = data?.items ?? [];
  const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / (data?.page_size ?? 20)));

  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold">Analysis history</h1>
      {items.length === 0 ? (
        <Card>
          <EmptyState message="No analyses yet. Start one from the Analyze page." />
        </Card>
      ) : (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-gray-400">
              <tr className="border-b border-base-700">
                <th className="py-2 pr-3">Username</th>
                <th className="px-2">Date</th>
                <th className="px-2">Status</th>
                <th className="px-2 text-right">Posts</th>
                <th className="pl-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((job) => (
                <tr key={job.id} className="border-b border-base-800">
                  <td className="py-2 pr-3 font-medium text-gray-200">@{job.username}</td>
                  <td className="px-2 text-gray-400">{formatDate(job.created_at)}</td>
                  <td className="px-2">
                    <Badge tone={STATUS_TONE[job.status]}>{job.status}</Badge>
                  </td>
                  <td className="px-2 text-right text-gray-300">{job.actual_post_count}</td>
                  <td className="pl-2 text-right">
                    <div className="flex justify-end gap-2">
                      {job.status === "completed" && (
                        <Link
                          href={`/analysis/${job.id}`}
                          className="rounded border border-base-600 px-2 py-1 text-xs hover:border-accent"
                        >
                          View
                        </Link>
                      )}
                      <button
                        onClick={async () => {
                          const j = await refresh.mutateAsync(job.id);
                          router.push(`/analysis/${j.id}`);
                        }}
                        className="rounded border border-base-600 px-2 py-1 text-xs hover:border-accent"
                      >
                        Refresh
                      </button>
                      <button
                        onClick={() => del.mutate(job.id)}
                        className="rounded border border-red-700/40 px-2 py-1 text-xs text-red-300 hover:bg-red-900/20"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-center gap-3 text-sm">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            className="rounded border border-base-600 px-3 py-1 disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-gray-400">
            Page {page} of {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="rounded border border-base-600 px-3 py-1 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
