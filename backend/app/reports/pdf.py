"""PDF report generation with ReportLab.

Builds the full 15-section behavioral report from an assembled analysis dict.
The report uses careful, non-diagnostic language and always includes the
methodology, data-limitation, and ethical-use sections.

Safety: no remote resources are fetched while rendering (no avatar/image URLs
are loaded), avoiding SSRF and keeping generation deterministic and offline.
"""

from __future__ import annotations

from datetime import datetime

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_ACCENT = colors.HexColor("#2a78d6")
_DARK = colors.HexColor("#111827")
_MUTED = colors.HexColor("#52514e")
_WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("XTitle", parent=s["Title"], fontSize=20, textColor=_DARK))
    s.add(ParagraphStyle("XH2", parent=s["Heading2"], fontSize=13, textColor=_ACCENT,
                         spaceBefore=12, spaceAfter=4))
    s.add(ParagraphStyle("XBody", parent=s["BodyText"], fontSize=9.5, leading=13,
                         alignment=TA_LEFT))
    s.add(ParagraphStyle("XSmall", parent=s["BodyText"], fontSize=8, textColor=_MUTED,
                         leading=10))
    s.add(ParagraphStyle("XDisclaim", parent=s["BodyText"], fontSize=8.5, leading=12,
                         textColor=_MUTED, backColor=colors.HexColor("#f4f4f2"),
                         borderPadding=6))
    return s


def _kv_table(rows: list[tuple[str, str]]) -> Table:
    data = [[k, v] for k, v in rows]
    t = Table(data, colWidths=[5 * cm, 11.5 * cm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), _MUTED),
        ("TEXTCOLOR", (1, 0), (1, -1), _DARK),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e5e3")),
    ]))
    return t


def _weekly_chart(weekly: list[int]) -> Drawing:
    d = Drawing(400, 130)
    chart = VerticalBarChart()
    chart.x = 20
    chart.y = 15
    chart.width = 360
    chart.height = 95
    chart.data = [weekly or [0] * 7]
    chart.categoryAxis.categoryNames = _WEEKDAYS
    chart.bars[0].fillColor = _ACCENT
    chart.valueAxis.valueMin = 0
    chart.barLabels.nudge = 7
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.labels.fontSize = 7
    d.add(chart)
    return d


def _score_meter(score: int) -> Drawing:
    d = Drawing(400, 40)
    d.add(Rect(0, 12, 300, 14, fillColor=colors.HexColor("#e5e5e3"), strokeColor=None))
    band = colors.HexColor("#199e70")
    if score >= 70:
        band = colors.HexColor("#e34948")
    elif score >= 40:
        band = colors.HexColor("#eda100")
    d.add(Rect(0, 12, max(0, min(100, score)) * 3, 14, fillColor=band, strokeColor=None))
    d.add(String(310, 14, f"{score}/100", fontSize=11, fillColor=_DARK))
    return d


def _fmt_dt(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, AttributeError):
        return str(iso)


def generate_report_pdf(report: dict, output_path: str) -> str:
    """Render `report` (assembled analysis dict) to a PDF at output_path."""
    s = _styles()
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=1.6 * cm, bottomMargin=1.6 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
        title="X Behavior Analysis Report",
    )
    profile = report.get("profile", {})
    job = report.get("job", {})
    activity = report.get("activity_metrics", {})
    content = report.get("content_metrics", {})
    sentiment = report.get("sentiment_metrics", {})
    engagement = report.get("engagement_metrics", {})
    patterns = report.get("pattern_metrics", {})
    summary = report.get("summary", {})
    dq = report.get("data_quality", {})
    source_label = (
        "Imported CSV"
        if dq.get("is_imported")
        else "Mock (demonstration data)"
        if dq.get("is_mock")
        else "Official X API"
    )
    source_description = (
        "imported CSV data"
        if dq.get("is_imported")
        else "mock demonstration data"
        if dq.get("is_mock")
        else "the official X API"
    )

    username = profile.get("username") or job.get("username", "unknown")
    story: list = []

    # 1-4. Title + identity + period + count
    story.append(Paragraph("X Behavior Analysis Report", s["XTitle"]))
    story.append(Paragraph(
        f"Observable posting-pattern analysis for <b>@{username}</b>", s["XBody"]))
    story.append(Spacer(1, 4))
    story.append(_kv_table([
        ("Analysis generated", _fmt_dt(dq.get("generated_at"))),
        ("Data period covered", f"{_fmt_dt(dq.get('earliest_post'))}  →  {_fmt_dt(dq.get('latest_post'))}"),
        ("Posts analyzed", str(dq.get("post_count", activity.get("post_count", 0)))),
        ("Data source", source_label),
        ("Detected language", dq.get("detected_language") or "—"),
        ("Methodology version", dq.get("methodology_version", "—")),
        ("Confidence", "LOW — insufficient data" if dq.get("low_confidence") else "Standard"),
    ]))
    if dq.get("is_mock"):
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            "NOTE: This report was generated from demonstration (mock) data.",
            s["XSmall"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e5e5e3"),
                            spaceBefore=8, spaceAfter=4))

    # 5. Profile overview
    story.append(Paragraph("Profile overview", s["XH2"]))
    story.append(_kv_table([
        ("Display name", str(profile.get("display_name") or "—")),
        ("Verified", "Yes" if profile.get("verified") else "No"),
        ("Account created", _fmt_dt(profile.get("created_at"))),
        ("Followers", _num(profile.get("followers_count"))),
        ("Following", _num(profile.get("following_count"))),
        ("Total public posts", _num(profile.get("tweet_count"))),
    ]))

    # 6. Executive summary
    story.append(Paragraph("Executive summary", s["XH2"]))
    if summary.get("headline"):
        story.append(Paragraph(summary["headline"], s["XBody"]))
    if summary.get("findings"):
        story.append(_bullets(summary["findings"], s))

    # 7. Posting activity
    story.append(Paragraph("Posting activity", s["XH2"]))
    comp = activity.get("composition", {})
    story.append(_kv_table([
        ("Posts per day", str(activity.get("posts_per_day", "—"))),
        ("Posts per week", str(activity.get("posts_per_week", "—"))),
        ("Median minutes between posts", str(activity.get("median_minutes_between_posts") or "—")),
        ("Most active hour", _hour(activity.get("most_active_hour"), activity.get("timezone", "UTC"))),
        ("Most active weekday", (activity.get("most_active_weekday") or {}).get("name", "—")),
        ("Original / Reply / Repost / Quote",
         f"{comp.get('original', 0)} / {comp.get('reply', 0)} / {comp.get('repost', 0)} / {comp.get('quote', 0)}"),
        ("Posting bursts detected", str(activity.get("burst_count", 0))),
        ("Longest inactive gap (hours)", str(activity.get("longest_inactive_hours") or "—")),
    ]))
    story.append(Paragraph("Weekly posting distribution", s["XSmall"]))
    story.append(_weekly_chart(activity.get("weekly_distribution", [0] * 7)))

    # 8. Content & topics
    story.append(Paragraph("Content and topic analysis", s["XH2"]))
    story.append(_kv_table([
        ("Average post length (chars)", str(content.get("avg_post_length", "—"))),
        ("Duplicate / near-duplicate ratio", _pct(content.get("duplicate_ratio"))),
        ("Top keywords", _joined(content.get("top_keywords"), "term")),
        ("Top hashtags", _joined(content.get("top_hashtags"), "tag", "#")),
        ("Top mentions", _joined(content.get("top_mentions"), "username", "@")),
        ("Top domains", _joined(content.get("top_domains"), "domain")),
        ("Dominant topics", ", ".join(t.get("topic", "") for t in content.get("dominant_topics", [])) or "—"),
    ]))

    # 9. Sentiment
    story.append(Paragraph("Sentiment analysis", s["XH2"]))
    if sentiment.get("available"):
        dist = sentiment.get("distribution", {})
        story.append(_kv_table([
            ("Model", sentiment.get("model", "vader")),
            ("Positive", _pct_val(dist.get("positive"))),
            ("Neutral", _pct_val(dist.get("neutral"))),
            ("Negative", _pct_val(dist.get("negative"))),
            ("Average compound score", str(sentiment.get("average_compound", "—"))),
            ("Posts analyzed / skipped (unsupported)",
             f"{sentiment.get('analyzed_count', 0)} / {sentiment.get('skipped_unsupported', 0)}"),
        ]))
    else:
        story.append(Paragraph(
            f"Sentiment unavailable ({sentiment.get('reason', 'insufficient data')}).", s["XBody"]))
    for lim in sentiment.get("limitations", [])[:3]:
        story.append(Paragraph(f"• {lim}", s["XSmall"]))

    # 10. Engagement
    story.append(Paragraph("Engagement analysis", s["XH2"]))
    if engagement.get("available"):
        avg = engagement.get("averages", {})
        story.append(_kv_table([
            ("Avg engagement per post", str(engagement.get("avg_engagement_per_post", "—"))),
            ("Median engagement", str(engagement.get("median_engagement", "—"))),
            ("Avg likes / replies / reposts",
             f"{avg.get('likes', 0)} / {avg.get('replies', 0)} / {avg.get('reposts', 0)}"),
            ("Approx engagement rate",
             (f"{engagement.get('approx_engagement_rate')}%"
              if engagement.get("approx_engagement_rate") is not None else "—")),
            ("Total engagement", _num(engagement.get("total_engagement"))),
        ]))
        story.append(Paragraph(engagement.get("time_window_note", ""), s["XSmall"]))
    else:
        story.append(Paragraph("Engagement metrics unavailable.", s["XBody"]))

    # 11-12. Pattern indicators + score
    story.append(Paragraph("Pattern indicators & automation-pattern score", s["XH2"]))
    story.append(_score_meter(int(patterns.get("automation_pattern_score", 0))))
    story.append(Spacer(1, 2))
    story.append(Paragraph(
        patterns.get("disclaimer",
                     "This score represents observable posting patterns and is not proof "
                     "that the account is automated or operated by a bot."), s["XSmall"]))
    comp_rows = [(c.get("label", ""), f"{c.get('points', 0)}/{c.get('max_points', 0)}")
                 for c in patterns.get("components", [])]
    if comp_rows:
        story.append(Spacer(1, 4))
        story.append(_kv_table(comp_rows))
    present = [i.get("label") for i in patterns.get("indicators", []) if i.get("present")]
    story.append(Paragraph(
        "Observable signals present: " + (", ".join(present) if present else "none"), s["XSmall"]))

    # 13. Methodology
    story.append(Paragraph("Methodology", s["XH2"]))
    story.append(Paragraph(
        "Public profile and post data were retrieved through the configured provider "
        f"({source_description}). "
        "Activity, content, sentiment (English VADER lexicon), engagement, and pattern "
        "metrics were computed deterministically. The automation-pattern score is the "
        "sum of six independently-capped, individually-explained components; thresholds "
        f"are configurable. Methodology version {dq.get('methodology_version', '1.0.0')}.",
        s["XBody"]))

    # 14. Data limitations
    story.append(Paragraph("Data limitations", s["XH2"]))
    limitations = [
        f"Only {dq.get('post_count', 0)} recent public post(s) were analyzed; older activity is not included.",
        "Engagement accumulates over time, so recent posts may appear to underperform.",
        "Sentiment is an approximation and does not reliably detect sarcasm or irony.",
        "Non-public data (DMs, protected posts, deleted posts) is never accessed.",
    ]
    if dq.get("low_confidence"):
        limitations.insert(0, "LOW CONFIDENCE: the sample is below the recommended minimum, "
                              "so findings may not be representative.")
    story.append(_bullets(limitations, s))

    # 15. Ethical-use disclaimer
    story.append(Paragraph("Ethical-use disclaimer", s["XH2"]))
    story.append(Paragraph(
        "This report describes <b>observable public posting patterns only</b>. It does "
        "not determine or infer personality, mental health, beliefs, intent, criminality, "
        "political identity, or whether an account is definitively operated by a bot. "
        "Scores and indicators are observational signals, not confirmed facts, and must "
        "not be used to make consequential decisions about any individual.", s["XDisclaim"]))

    doc.build(story)
    return output_path


# --- small formatting helpers ---
def _num(v) -> str:
    return f"{v:,}" if isinstance(v, (int, float)) else "—"


def _pct(v) -> str:
    return f"{round((v or 0) * 100)}%" if v is not None else "—"


def _pct_val(v) -> str:
    return f"{v}%" if v is not None else "—"


def _hour(h, tz) -> str:
    if not h:
        return "—"
    return f"{h.get('hour', 0):02d}:00 ({tz})"


def _joined(items, key, prefix="") -> str:
    if not items:
        return "—"
    return ", ".join(f"{prefix}{i.get(key, '')}" for i in items[:8])


def _bullets(items, s) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(str(i), s["XBody"]), leftIndent=10) for i in items],
        bulletType="bullet", start="•",
    )
