"""use longtext for mysql payload columns

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-26 10:30:00.000000+08:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


MYSQL_LONGTEXT_COLUMNS = {
    "biz_task_model_calls": ("request_payload_json", "response_payload_json", "error_message"),
    "biz_material_assets": ("metadata_json", "rating_note"),
    "biz_task_status_history": ("message", "payload_json"),
    "biz_task_stage_runs": ("input_summary_json", "output_summary_json", "error_message"),
    "biz_task_attempts": ("failure_message", "payload_json"),
    "biz_task_queue_events": ("payload_json",),
    "biz_task_results": ("reason", "extra_json"),
    "biz_tasks": (
        "description",
        "request_payload_json",
        "context_json",
        "intro_template",
        "outro_template",
        "creative_prompt",
        "error_message",
        "plan_json",
    ),
    "biz_stage_versions": ("input_summary_json", "output_summary_json", "model_call_summary_json"),
    "biz_stage_workflows": ("transcript_text", "global_prompt", "auto_pilot_error_message", "metadata_json"),
}


def upgrade() -> None:
    if op.get_bind().dialect.name != "mysql":
        return
    for table_name, column_names in MYSQL_LONGTEXT_COLUMNS.items():
        with op.batch_alter_table(table_name) as batch_op:
            for column_name in column_names:
                batch_op.alter_column(column_name, existing_type=sa.Text(), type_=mysql.LONGTEXT())


def downgrade() -> None:
    if op.get_bind().dialect.name != "mysql":
        return
    for table_name, column_names in MYSQL_LONGTEXT_COLUMNS.items():
        with op.batch_alter_table(table_name) as batch_op:
            for column_name in column_names:
                batch_op.alter_column(column_name, existing_type=mysql.LONGTEXT(), type_=sa.Text())
