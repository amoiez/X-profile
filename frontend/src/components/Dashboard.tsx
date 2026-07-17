"use client";

import { useRefreshAnalysis } from "@/lib/queries";
import { useRouter } from "next/navigation";

import {
  ContentTypeChart,
  HourlyHeatmap,
  SentimentDoughnut,
  SentimentTrendChart,
  TopicsChart,
  WeeklyActivityChart,
} from "@/components/charts";
import { PatternPanel } from "@/components/PatternPanel";
import { TopPostsTable } from "@/components/TopPostsTable";
import { Badge, Card, Stat } from "@/components/ui";
import { compactNumber, formatDate, fullNumber } from "@/lib/format";
import type { ResultsResponse } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "/api/v1";

function accountAge(iso?: string | null): string {
  if (!iso) return "—";
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days < 0) return "—";
  const years = Math.floor(days / 365);
  return years >= 1 ? `${years}y` : `${days}d`;
}

export function Dashboard({ data }: { data: ResultsResponse }) {
  const router = useRouter();
  const refresh = useRefreshAnalysis();
  const {
    job,
    profile,
    activity_metrics: activity,
    content_metrics: content,
    sentiment_metrics: sentiment,
    engagement_metrics: engagement,
    pattern_metrics: patterns,
    summary,
    data_quality: dq,
  } = data;

  const topics = (content.dominant_topics?.length
    ? content.dominant_topics.map((t) => ({ label: t.topic, value: Math.round(t.weight * 1000) }))
    : content.top_keywords.slice(0, 8).map((k) => ({ label: k.term, value: k.count }))
  ).slice(0, 8);

  const onRefresh = async () => {
    const j = await refresh.mutateAsync(job.id);
    router.push(`/analysis/${j.id}`);
  };

  const followerRatio =
    profile.followers_count && profile.following_count
      ? (profile.followers_count / Math.max(1, profile.following_count)).toFixed(2)
      : "—";

  return (
    <div className="space-y-6">
      {/* Header / profile */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-4">
          {profile.profile_image_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={profile.profile_image_url}
              alt=""
              width={56}
              height={56}
              className="h-14 w-14 rounded-full border border-base-700"
            />
          )}
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-semibold">
                {profile.display_name || profile.username}
              </h1>
              {profile.verified && <Badge tone="accent">Verified</Badge>}
            </div>
            <div className="text-sm text-gray-400">@{profile.username}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {dq.is_mock ? (
            <Badge tone="warning">Demonstration data (mock)</Badge>
          ) : (
            <Badge tone="positive">Live X API data</Badge>
          )}
          {dq.low_confidence && <Badge tone="danger">Low confidence</Badge>}
          <button
            onClick={onRefresh}
            disabled={refresh.isPending}
            className="rounded-lg border border-base-600 px-3 py-1.5 text-sm hover:border-accent disabled:opacity-60"
          >
            {refresh.isPending ? "Refreshing…" : "Refresh"}
          </button>
          <a
            href={`${API_BASE}/analyses/${job.id}/report.pdf`}
            className="rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-base-900 hover:bg-accent-muted"
          >
            Download PDF
          </a>
        </div>
      </div>

      {profile.bio && <p className="text-sm text-gray-400">{profile.bio}</p>}

      {dq.low_confidence && (
        <div className="rounded-lg border border-red-700/40 bg-red-900/15 px-4 py-3 text-sm text-red-200">
          Low confidence due to insufficient data: only {dq.post_count} post(s)
          analyzed (threshold {dq.low_confidence_threshold}). Findings may not be
          representative.
        </div>
      )}

      {/* Executive summary */}
      <Card title="Executive summary">
        <p className="text-gray-200">{summary.headline}</p>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-gray-300">
          {summary.findings.map((f, i) => (
            <li key={i}>{f}</li>
          ))}
        </ul>
      </Card>

      {/* Key metrics */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <Stat label="Posts analyzed" value={fullNumber(activity.post_count)} />
        <Stat label="Posts / day" value={activity.posts_per_day} />
        <Stat
          label="Most active hour"
          value={activity.most_active_hour ? `${String(activity.most_active_hour.hour).padStart(2, "0")}:00` : "—"}
          hint={activity.timezone}
        />
        <Stat label="Followers" value={compactNumber(profile.followers_count)} hint={`ratio ${followerRatio}`} />
        <Stat
          label="Avg engagement"
          value={compactNumber(engagement.avg_engagement_per_post)}
          hint={engagement.approx_engagement_rate != null ? `${engagement.approx_engagement_rate}% rate` : undefined}
        />
        <Stat label="Account age" value={accountAge(profile.created_at)} />
      </div>

      {/* Activity */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Weekly posting activity" subtitle={`Timezone: ${activity.timezone}`}>
          <WeeklyActivityChart data={activity.weekly_distribution} />
        </Card>
        <Card title="Hourly activity heatmap">
          <HourlyHeatmap data={activity.hourly_distribution} />
        </Card>
      </div>

      {/* Sentiment */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card
          title="Sentiment distribution"
          subtitle={sentiment.available ? `Model: ${sentiment.model}` : "Unavailable"}
        >
          {sentiment.available ? (
            <SentimentDoughnut distribution={sentiment.distribution} />
          ) : (
            <p className="text-sm text-gray-400">
              Sentiment unavailable ({sentiment.reason || "insufficient data"}).
            </p>
          )}
        </Card>
        <Card title="Sentiment trend" subtitle="Average compound score by day">
          {sentiment.available ? (
            <SentimentTrendChart data={sentiment.trend} />
          ) : (
            <p className="text-sm text-gray-400">No trend available.</p>
          )}
        </Card>
      </div>

      {/* Content & engagement */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Top topics & keywords">
          <TopicsChart data={topics} />
        </Card>
        <Card title="Engagement by content type">
          <ContentTypeChart data={engagement.by_content_type} />
        </Card>
      </div>

      {/* Pattern score */}
      <PatternPanel patterns={patterns} />

      {/* Top posts */}
      <Card title="Top-performing posts" subtitle={engagement.time_window_note}>
        <TopPostsTable engagement={engagement} />
      </Card>

      {/* Methodology & limitations */}
      <Card title="Methodology & data limitations">
        <div className="grid gap-4 text-sm text-gray-300 md:grid-cols-2">
          <ul className="space-y-1">
            <li>Posts analyzed: <strong>{dq.post_count}</strong></li>
            <li>Data period: {formatDate(dq.earliest_post)} → {formatDate(dq.latest_post)}</li>
            <li>Detected language: {dq.detected_language || "—"}</li>
            <li>Data source: {dq.is_mock ? "Mock (demonstration)" : "X API"}</li>
          </ul>
          <ul className="space-y-1">
            <li>Methodology version: {dq.methodology_version}</li>
            <li>Report generated: {formatDate(dq.generated_at)}</li>
            <li>Confidence: {dq.low_confidence ? "Low (insufficient data)" : "Standard"}</li>
            {sentiment.limitations?.slice(0, 1).map((l, i) => <li key={i}>{l}</li>)}
          </ul>
        </div>
        <p className="mt-4 rounded-lg border border-yellow-700/30 bg-yellow-900/10 p-3 text-xs text-yellow-200/80">
          This report describes observable public posting patterns only. It does not
          determine personality, mental health, beliefs, intent, or whether an
          account is definitively automated.
        </p>
      </Card>
    </div>
  );
}
