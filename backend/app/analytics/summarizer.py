"""Template-based executive summary generator.

Uses calculated statistics and deliberately careful, non-diagnostic language.
It never claims personality, intent, identity, or that an account is a bot.
An optional LLM summarizer may be layered on later, receiving only aggregated
statistics — never raw personal data.
"""

from __future__ import annotations

from app import METHODOLOGY_VERSION


def build_summary(
    *,
    profile: dict,
    activity: dict,
    content: dict | None = None,
    sentiment: dict | None = None,
    engagement: dict | None = None,
    patterns: dict | None = None,
    data_quality: dict,
) -> dict:
    """Return a structured summary: headline + careful bullet findings."""
    username = profile.get("username", "this account")
    n = activity.get("post_count", 0)

    findings: list[str] = []

    if data_quality.get("low_confidence"):
        findings.append(
            "Fewer than the recommended number of posts were available, so "
            "these observations are low confidence and may not be representative."
        )

    if n:
        ppd = activity.get("posts_per_day")
        if ppd is not None:
            findings.append(
                f"Within the analyzed period, the account posted about "
                f"{ppd:g} times per day on average."
            )
        hr = activity.get("most_active_hour")
        wd = activity.get("most_active_weekday")
        tz = activity.get("timezone", "UTC")
        if hr and wd:
            findings.append(
                f"The collected posts indicate the account appears most active "
                f"around {hr['hour']:02d}:00 ({tz}) and on {wd['name']}s."
            )
        comp = activity.get("composition", {})
        pct = comp.get("percentages", {})
        if pct:
            findings.append(
                "Post composition within the sample was approximately "
                f"{pct.get('original', 0):g}% original, {pct.get('reply', 0):g}% replies, "
                f"and {pct.get('repost', 0):g}% reposts."
            )
        if activity.get("burst_count"):
            findings.append(
                f"The system detected {activity['burst_count']} short posting "
                "burst(s) within the collected data."
            )

    if sentiment and sentiment.get("available"):
        dist = sentiment.get("distribution", {})
        findings.append(
            "Sentiment across analyzed posts was approximately "
            f"{dist.get('positive', 0):g}% positive, {dist.get('neutral', 0):g}% neutral, "
            f"and {dist.get('negative', 0):g}% negative."
        )

    if patterns and "automation_pattern_score" in patterns:
        score = patterns["automation_pattern_score"]
        findings.append(
            f"The observable posting-pattern (automation) score is {score}/100. "
            "This score reflects observable posting patterns and is not proof "
            "that the account is automated or operated by a bot."
        )

    headline = (
        f"Within the analyzed sample of {n} post(s), "
        f"{username} shows the observable posting patterns summarized below. "
        "These describe public activity only and are not conclusions about the "
        "person, their beliefs, or their intent."
    )

    return {
        "headline": headline,
        "findings": findings,
        "methodology_version": METHODOLOGY_VERSION,
    }
