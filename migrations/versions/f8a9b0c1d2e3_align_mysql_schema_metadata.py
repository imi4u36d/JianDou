"""align mysql schema metadata after longtext migration

Revision ID: f8a9b0c1d2e3
Revises: f7a8b9c0d1e2
Create Date: 2026-06-26 23:25:00.000000+08:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "f8a9b0c1d2e3"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


MYSQL_LONGTEXT_COLUMNS = {
    "biz_task_model_calls": {
        "request_payload_json": (False, "Sanitized provider request payload JSON.", "{}"),
        "response_payload_json": (False, "Sanitized provider response payload JSON.", "{}"),
        "error_message": (True, "Human-readable provider error message.", None),
    },
    "biz_material_assets": {
        "metadata_json": (True, "Additional media metadata JSON.", None),
        "rating_note": (True, "Optional note attached to user_rating.", None),
    },
    "biz_task_status_history": {
        "message": (True, "Human-readable status or trace message.", None),
        "payload_json": (True, "Structured event payload JSON.", None),
    },
    "biz_task_stage_runs": {
        "input_summary_json": (False, "Condensed stage input summary JSON.", "{}"),
        "output_summary_json": (False, "Condensed stage output summary JSON.", "{}"),
        "error_message": (True, "Human-readable stage error message.", None),
    },
    "biz_task_attempts": {
        "failure_message": (True, "Human-readable attempt failure message.", None),
        "payload_json": (False, "Attempt execution payload JSON.", "{}"),
    },
    "biz_task_queue_events": {
        "payload_json": (False, "Structured queue event metadata JSON.", "{}"),
    },
    "biz_task_results": {
        "reason": (False, "Generation or selection reason for this result.", ""),
        "extra_json": (True, "Additional result metadata JSON.", None),
    },
    "biz_tasks": {
        "description": (True, "Optional user-facing task description.", None),
        "request_payload_json": (True, "Immutable request snapshot used to reproduce the task.", None),
        "context_json": (True, "Mutable execution context produced by planning/rendering stages.", None),
        "intro_template": (True, "Selected intro template key or serialized template data.", None),
        "outro_template": (True, "Selected outro template key or serialized template data.", None),
        "creative_prompt": (True, "User prompt or generated creative prompt used for the task.", None),
        "error_message": (True, "Human-readable terminal error message.", None),
        "plan_json": (True, "Deprecated: historical plan payload. Prefer context_json/storyboard artifacts.", None),
    },
    "biz_stage_versions": {
        "input_summary_json": (False, "Condensed input snapshot JSON.", "{}"),
        "output_summary_json": (False, "Condensed output snapshot JSON.", "{}"),
        "model_call_summary_json": (False, "Condensed model invocation summary JSON.", "{}"),
    },
    "biz_stage_workflows": {
        "transcript_text": (True, "Source transcript or creative brief for storyboard generation.", None),
        "global_prompt": (True, "Optional global prompt applied across stages.", None),
        "auto_pilot_error_message": (False, "Error message when auto-pilot entered failed state.", ""),
        "metadata_json": (False, "Mutable workflow metadata JSON.", "{}"),
    },
}

PUBLIC_SHARE_DEFAULT_COLUMNS = {
    "biz_public_shares": {
        "title": (sa.String(length=255), False, "Display title captured at share time.", ""),
        "status": (sa.String(length=32), False, "Share visibility status.", "ACTIVE"),
        "like_count": (sa.Integer(), False, "Cached active like count.", "0"),
        "is_deleted": (sa.Integer(), False, "Soft delete flag: 0 active, 1 deleted.", "0"),
        "remark": (sa.String(length=512), False, "Operator remark; not used for core business logic.", ""),
    },
    "biz_public_share_likes": {
        "is_deleted": (sa.Integer(), False, "Soft delete flag: 0 active, 1 removed.", "0"),
        "remark": (sa.String(length=512), False, "Operator remark; not used for core business logic.", ""),
    },
}


def upgrade() -> None:
    if op.get_bind().dialect.name != "mysql":
        return
    _restore_longtext_metadata()
    _drop_public_share_server_defaults()


def downgrade() -> None:
    if op.get_bind().dialect.name != "mysql":
        return
    _restore_public_share_server_defaults()


def _restore_longtext_metadata() -> None:
    for table_name, columns in MYSQL_LONGTEXT_COLUMNS.items():
        for column_name, (nullable, _comment, fallback) in columns.items():
            if nullable or fallback is None:
                continue
            table = sa.table(table_name, sa.column(column_name, mysql.LONGTEXT()))
            op.execute(table.update().where(table.c[column_name].is_(None)).values({column_name: fallback}))
        with op.batch_alter_table(table_name) as batch_op:
            for column_name, (nullable, comment, _fallback) in columns.items():
                batch_op.alter_column(
                    column_name,
                    existing_type=mysql.LONGTEXT(),
                    existing_nullable=True,
                    nullable=nullable,
                    existing_comment=None,
                    comment=comment,
                )


def _drop_public_share_server_defaults() -> None:
    for table_name, columns in PUBLIC_SHARE_DEFAULT_COLUMNS.items():
        with op.batch_alter_table(table_name) as batch_op:
            for column_name, (column_type, nullable, comment, _default) in columns.items():
                batch_op.alter_column(
                    column_name,
                    existing_type=column_type,
                    existing_nullable=nullable,
                    existing_comment=comment,
                    server_default=None,
                )


def _restore_public_share_server_defaults() -> None:
    for table_name, columns in PUBLIC_SHARE_DEFAULT_COLUMNS.items():
        with op.batch_alter_table(table_name) as batch_op:
            for column_name, (column_type, nullable, comment, default) in columns.items():
                batch_op.alter_column(
                    column_name,
                    existing_type=column_type,
                    existing_nullable=nullable,
                    existing_comment=comment,
                    server_default=default,
                )
