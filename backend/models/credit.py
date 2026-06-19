from __future__ import annotations

from sqlalchemy import CheckConstraint, Column, Index, Integer, String, Text

from backend.database import Base


class SysCreditAccount(Base):
    __tablename__ = "sys_credit_account"
    __table_args__ = (
        CheckConstraint("balance >= 0", name="ck_sys_credit_account_balance_non_negative"),
        CheckConstraint("total_consumed >= 0", name="ck_sys_credit_account_total_consumed_non_negative"),
        Index("ix_sys_credit_account_user", "user_id"),
        {"comment": "Current credit balance for each user."},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Internal numeric primary key.")
    user_id = Column(Integer, nullable=False, unique=True, comment="Owner sys_user.id.")
    balance = Column(Integer, nullable=False, default=0, comment="Current spendable credit balance.")
    total_consumed = Column(Integer, nullable=False, default=0, comment="Cumulative consumed credits.")
    total_adjusted = Column(Integer, nullable=False, default=0, comment="Cumulative manual adjustment delta.")
    created_at = Column(String(32), nullable=False, comment="ISO timestamp when the account was created.")
    updated_at = Column(String(32), nullable=False, comment="ISO timestamp when the account was last updated.")


class SysCreditRule(Base):
    __tablename__ = "sys_credit_rule"
    __table_args__ = (
        CheckConstraint("cost >= 0", name="ck_sys_credit_rule_cost_non_negative"),
        {"comment": "Credit cost rule per billable feature."},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Internal numeric primary key.")
    feature_code = Column(String(64), nullable=False, unique=True, comment="Billable feature code, e.g. IMAGE_GENERATION.")
    display_name = Column(String(128), nullable=False, default="", comment="Human-readable feature name.")
    cost = Column(Integer, nullable=False, default=0, comment="Credits consumed per use.")
    created_at = Column(String(32), nullable=False, comment="ISO timestamp when the rule was created.")
    updated_at = Column(String(32), nullable=False, comment="ISO timestamp when the rule was last updated.")


class SysCreditTransaction(Base):
    __tablename__ = "sys_credit_transaction"
    __table_args__ = (
        CheckConstraint(
            "transaction_type in ('CONSUME', 'USAGE', 'REFUND', 'ADJUST')",
            name="ck_sys_credit_transaction_type",
        ),
        CheckConstraint("balance_before >= 0", name="ck_sys_credit_transaction_balance_before_non_negative"),
        CheckConstraint("balance_after >= 0", name="ck_sys_credit_transaction_balance_after_non_negative"),
        Index("ix_sys_credit_transaction_user_created", "user_id", "created_at"),
        {"comment": "Append-only ledger of credit balance changes."},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Internal numeric primary key.")
    transaction_id = Column(String(64), nullable=False, unique=True, comment="Public stable ledger transaction id.")
    user_id = Column(Integer, nullable=False, comment="Owner sys_user.id.")
    feature_code = Column(String(64), nullable=True, comment="Billable feature code when the transaction is feature-driven.")
    transaction_type = Column(String(32), nullable=False, comment="Transaction type: CONSUME, USAGE, REFUND or ADJUST.")
    amount_delta = Column(Integer, nullable=False, comment="Signed credit delta applied to balance.")
    balance_before = Column(Integer, nullable=False, comment="Balance immediately before applying this transaction.")
    balance_after = Column(Integer, nullable=False, comment="Balance immediately after applying this transaction.")
    related_run_id = Column(String(64), nullable=True, comment="Optional generation run id associated with the transaction.")
    related_task_id = Column(String(64), nullable=True, comment="Optional task id associated with the transaction.")
    related_workflow_id = Column(String(64), nullable=True, comment="Optional workflow id associated with the transaction.")
    reason = Column(Text, nullable=True, comment="Human-readable audit reason.")
    metadata_json = Column(Text, nullable=True, comment="Optional structured metadata JSON.")
    created_at = Column(String(32), nullable=False, comment="ISO timestamp when the transaction was recorded.")
