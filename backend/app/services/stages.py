"""Analysis pipeline stages and their progress checkpoints.

Progress is a 0-100 integer stored on the job row and surfaced to the UI.
Content/sentiment/engagement/patterns stages are wired here now; their engines
are implemented in Milestone 3.
"""

from __future__ import annotations

# (stage_key, human_label, progress_percent_when_complete)
STAGE_VALIDATING = "validating"
STAGE_RETRIEVING_PROFILE = "retrieving_profile"
STAGE_RETRIEVING_POSTS = "retrieving_posts"
STAGE_ACTIVITY = "activity"
STAGE_CONTENT = "content"
STAGE_SENTIMENT = "sentiment"
STAGE_ENGAGEMENT = "engagement"
STAGE_PATTERNS = "patterns"
STAGE_SUMMARY = "generating_report"
STAGE_DONE = "done"

STAGE_PROGRESS: dict[str, int] = {
    STAGE_VALIDATING: 5,
    STAGE_RETRIEVING_PROFILE: 20,
    STAGE_RETRIEVING_POSTS: 40,
    STAGE_ACTIVITY: 55,
    STAGE_CONTENT: 70,
    STAGE_SENTIMENT: 82,
    STAGE_ENGAGEMENT: 92,
    STAGE_PATTERNS: 97,
    STAGE_SUMMARY: 99,
    STAGE_DONE: 100,
}

STAGE_LABELS: dict[str, str] = {
    STAGE_VALIDATING: "Validating username",
    STAGE_RETRIEVING_PROFILE: "Retrieving public profile",
    STAGE_RETRIEVING_POSTS: "Retrieving posts",
    STAGE_ACTIVITY: "Calculating activity metrics",
    STAGE_CONTENT: "Running content analysis",
    STAGE_SENTIMENT: "Analyzing sentiment",
    STAGE_ENGAGEMENT: "Measuring engagement",
    STAGE_PATTERNS: "Detecting patterns",
    STAGE_SUMMARY: "Generating report",
    STAGE_DONE: "Complete",
}
