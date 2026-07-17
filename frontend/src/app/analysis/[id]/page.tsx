"use client";

import { useParams, useRouter } from "next/navigation";

import { Dashboard } from "@/components/Dashboard";
import { ErrorState } from "@/components/ErrorState";
import { ProgressView } from "@/components/ProgressView";
import { Spinner } from "@/components/ui";
import { useJob, useProgress, useRefreshAnalysis, useResults } from "@/lib/queries";

export default function AnalysisPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const refresh = useRefreshAnalysis();

  const job = useJob(id, !!id);
  const progress = useProgress(id, !!id);
  const status = progress.data?.status;
  const isDone = status === "completed";
  const isFailed = status === "failed";

  const results = useResults(id, isDone);

  if (progress.isLoading || (!progress.data && !progress.isError)) {
    return (
      <div className="flex justify-center py-20">
        <Spinner label="Loading analysis…" />
      </div>
    );
  }

  if (progress.isError) {
    return <ErrorState code="ANALYSIS_FAILED" message="This analysis could not be loaded." />;
  }

  if (isFailed) {
    return (
      <ErrorState
        code={progress.data?.error_code || "ANALYSIS_FAILED"}
        message={progress.data?.error_message}
        onRetry={async () => {
          const j = await refresh.mutateAsync(id);
          router.push(`/analysis/${j.id}`);
        }}
      />
    );
  }

  if (!isDone) {
    return (
      <ProgressView
        username={job.data?.username ?? "…"}
        progress={progress.data?.progress ?? 0}
        stage={progress.data?.current_stage ?? null}
      />
    );
  }

  if (results.isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner label="Building dashboard…" />
      </div>
    );
  }

  if (results.isError || !results.data) {
    return <ErrorState code="ANALYSIS_FAILED" message="Results could not be loaded." />;
  }

  return <Dashboard data={results.data} />;
}
