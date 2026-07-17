"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-18

Creates users, x_profiles, analysis_jobs, analysis_results, reports.
Uses portable types (String(36) ids, JSON metrics) so the same migration
runs on PostgreSQL and SQLite.
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), unique=True, nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("role", sa.String(16), nullable=False, server_default="user"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "x_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("platform_user_id", sa.String(64), nullable=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("public_profile_data", sa.JSON(), nullable=False),
        sa.Column("last_retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_x_profiles_username", "x_profiles", ["username"])
    op.create_index("ix_x_profiles_platform_user_id", "x_profiles", ["platform_user_id"])

    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("profile_id", sa.String(36), sa.ForeignKey("x_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_stage", sa.String(64), nullable=True),
        sa.Column("requested_post_limit", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("actual_post_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_source", sa.String(16), nullable=False, server_default="mock"),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_analysis_jobs_user_id", "analysis_jobs", ["user_id"])
    op.create_index("ix_analysis_jobs_profile_id", "analysis_jobs", ["profile_id"])
    op.create_index("ix_analysis_jobs_username", "analysis_jobs", ["username"])
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"])
    op.create_index("ix_analysis_jobs_created_at", "analysis_jobs", ["created_at"])

    op.create_table(
        "analysis_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("activity_metrics", sa.JSON(), nullable=False),
        sa.Column("content_metrics", sa.JSON(), nullable=False),
        sa.Column("sentiment_metrics", sa.JSON(), nullable=False),
        sa.Column("engagement_metrics", sa.JSON(), nullable=False),
        sa.Column("pattern_metrics", sa.JSON(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("data_quality", sa.JSON(), nullable=False),
        sa.Column("methodology_version", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_analysis_results_job_id", "analysis_results", ["job_id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format", sa.String(16), nullable=False, server_default="pdf"),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reports_job_id", "reports", ["job_id"])


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("analysis_results")
    op.drop_table("analysis_jobs")
    op.drop_table("x_profiles")
    op.drop_table("users")
