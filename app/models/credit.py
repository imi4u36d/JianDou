from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text

from app.database import Base


class SysCreditAccount(Base):
    __tablename__ = "sys_credit_account"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, unique=True)
    balance = Column(Integer, nullable=False, default=0)
    total_consumed = Column(Integer, nullable=False, default=0)
    total_adjusted = Column(Integer, nullable=False, default=0)
    created_at = Column(String(32), nullable=False)
    updated_at = Column(String(32), nullable=False)


class SysCreditRule(Base):
    __tablename__ = "sys_credit_rule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feature_code = Column(String(64), nullable=False, unique=True)
    display_name = Column(String(128), nullable=False, default="")
    cost = Column(Integer, nullable=False, default=0)
    created_at = Column(String(32), nullable=False)
    updated_at = Column(String(32), nullable=False)


class SysCreditTransaction(Base):
    __tablename__ = "sys_credit_transaction"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(64), nullable=False, unique=True)
    user_id = Column(Integer, nullable=False)
    feature_code = Column(String(64), nullable=True)
    transaction_type = Column(String(32), nullable=False)
    amount_delta = Column(Integer, nullable=False)
    balance_before = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    related_run_id = Column(String(64), nullable=True)
    related_task_id = Column(String(64), nullable=True)
    related_workflow_id = Column(String(64), nullable=True)
    reason = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(String(32), nullable=False)
