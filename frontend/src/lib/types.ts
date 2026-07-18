// Types mirroring the backend API v1 response shapes.

export type JobStatus = "pending" | "running" | "completed" | "failed";

export interface JobSummary {
  id: string;
  username: string;
  status: JobStatus;
  progress: number;
  current_stage: string | null;
  requested_post_limit: number;
  actual_post_count: number;
  data_source: string;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  period_start: string | null;
  period_end: string | null;
}

export interface ProgressResponse {
  id: string;
  status: JobStatus;
  progress: number;
  current_stage: string | null;
  error_code: string | null;
  error_message: string | null;
}

export interface Named {
  [key: string]: unknown;
}

export interface ActivityMetrics {
  post_count: number;
  timezone: string;
  posts_per_day: number;
  posts_per_week: number;
  median_minutes_between_posts: number | null;
  most_active_weekday: { index: number; name: string; count: number } | null;
  most_active_hour: { hour: number; count: number } | null;
  hourly_distribution: number[];
  weekly_distribution: number[];
  composition: {
    original: number;
    reply: number;
    repost: number;
    quote: number;
    percentages: Record<string, number>;
  };
  active_day_ratio: number;
  longest_inactive_hours: number | null;
  burst_count: number;
  span_days: number;
  first_post_at: string | null;
  last_post_at: string | null;
}

export interface ContentMetrics {
  post_count: number;
  top_keywords: { term: string; count: number }[];
  top_hashtags: { tag: string; count: number }[];
  top_mentions: { username: string; count: number }[];
  top_domains: { domain: string; count: number }[];
  dominant_topics: { topic: string; weight: number; terms: string[] }[];
  media_usage: Record<string, number> & { percentages: Record<string, number> };
  avg_post_length: number;
  avg_word_count: number;
  duplicate_ratio: number;
  unique_ratio: number;
  duplicate_groups: { text: string; count: number }[];
}

export interface SentimentMetrics {
  available: boolean;
  reason?: string;
  model: string;
  analyzed_count: number;
  skipped_unsupported: number;
  detected_language: string | null;
  distribution: { positive: number; neutral: number; negative: number };
  counts: { positive: number; neutral: number; negative: number };
  average_compound: number | null;
  trend: { date: string; average: number; count: number }[];
  by_hashtag: { hashtag: string; average: number; count: number }[];
  limitations: string[];
}

export interface EngagementMetrics {
  available: boolean;
  post_count: number;
  averages: Record<string, number>;
  medians: Record<string, number>;
  totals: Record<string, number>;
  total_engagement: number;
  avg_engagement_per_post: number;
  median_engagement: number;
  approx_engagement_rate: number | null;
  top_posts: {
    post_id: string;
    text: string;
    created_at: string;
    engagement: number;
    likes: number;
    replies: number;
    reposts: number;
    quotes: number;
    media_type: string;
  }[];
  by_content_type: { type: string; avg_engagement: number; count: number }[];
  by_weekday: number[];
  by_hour: number[];
  time_window_note: string;
}

export interface PatternComponent {
  key: string;
  label: string;
  points: number;
  max_points: number;
  explanation: string;
  signals: Record<string, unknown>;
}

export interface PatternMetrics {
  automation_pattern_score: number;
  disclaimer: string;
  components: PatternComponent[];
  signals_triggered: string[];
  indicators: { key: string; present: boolean; label: string; value: unknown }[];
}

export interface DataQuality {
  post_count: number;
  earliest_post: string | null;
  latest_post: string | null;
  detected_language: string | null;
  methodology_version: string;
  data_source: string;
  is_mock: boolean;
  is_imported?: boolean;
  generated_at: string;
  low_confidence: boolean;
  low_confidence_threshold: number;
  missing_metrics: string[];
}

export interface Summary {
  headline: string;
  findings: string[];
  methodology_version: string;
}

export interface ProfileData {
  username?: string;
  display_name?: string | null;
  bio?: string | null;
  created_at?: string | null;
  verified?: boolean;
  followers_count?: number | null;
  following_count?: number | null;
  tweet_count?: number | null;
  profile_image_url?: string | null;
}

export interface ResultsResponse {
  job: JobSummary;
  profile: ProfileData;
  activity_metrics: ActivityMetrics;
  content_metrics: ContentMetrics;
  sentiment_metrics: SentimentMetrics;
  engagement_metrics: EngagementMetrics;
  pattern_metrics: PatternMetrics;
  summary: Summary;
  data_quality: DataQuality;
  methodology_version: string;
}

export interface PaginatedJobs {
  items: JobSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApiErrorBody {
  error: { code: string; message: string; request_id: string | null };
}
