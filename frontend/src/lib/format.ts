export function compactNumber(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(n);
}

export function fullNumber(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return Intl.NumberFormat().format(n);
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function formatDateShort(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}

export const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export const ERROR_HINTS: Record<string, string> = {
  INVALID_USERNAME: "Enter a valid handle: 1–15 letters, digits, or underscores.",
  PROFILE_NOT_FOUND: "No public profile exists for that username.",
  PROFILE_PROTECTED: "This profile is protected, so its posts cannot be analyzed.",
  PROFILE_SUSPENDED: "This account is suspended or unavailable.",
  NO_POSTS_AVAILABLE: "This profile has no public posts to analyze.",
  CREDENTIALS_MISSING: "X API credentials are not configured on the server.",
  RATE_LIMITED: "The X API rate limit was reached. Try again shortly.",
  UNSUPPORTED_LANGUAGE: "The detected language isn't supported for full analysis.",
  ANALYSIS_FAILED: "The analysis could not be completed.",
  NETWORK_ERROR: "Could not reach the server. Check your connection.",
};
