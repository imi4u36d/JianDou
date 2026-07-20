from __future__ import annotations

from typing import Any, Literal

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field

from backend.schemas.common import _to_camel


class AdminRequestModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(validation_alias=_to_camel, serialization_alias=_to_camel),
        populate_by_name=True,
    )


class AdminOverviewResponse(AdminRequestModel):
    generated_at: str
    counts: dict[str, int]
    queue: dict[str, Any]
    workers: dict[str, Any]
    recent_tasks: list[dict[str, Any]] = Field(default_factory=list)
    recent_failures: list[dict[str, Any]] = Field(default_factory=list)
    recent_running_tasks: list[dict[str, Any]] = Field(default_factory=list)
    recent_trace_count: int = 0
    model_ready: bool = False
    primary_model: str | None = None
    text_model: str | None = None


class AdminTaskBatchResult(BaseModel):
    action: str = ""
    requested_count: int = 0
    succeeded_task_ids: list[str] = Field(default_factory=list)
    failed: list[dict] = Field(default_factory=list)


class AdminTaskBatchActionRequest(AdminRequestModel):
    action: Literal["terminate"] = "terminate"
    task_ids: list[str] = Field(default_factory=list, alias="taskIds")


class AdminModelProviderKeyRequest(AdminRequestModel):
    key: str
    api_key: str = Field(default="", alias="apiKey")


class AdminModelConfigKeysRequest(AdminRequestModel):
    providers: list[AdminModelProviderKeyRequest] = Field(default_factory=list)


class AdminCreateUserRequest(AdminRequestModel):
    username: str
    password: str
    role: str = "USER"
    status: str = "ACTIVE"
    task_concurrency_limit: int = 1


class AdminUpdateUserRequest(AdminRequestModel):
    role: str | None = None
    status: str | None = None
    task_concurrency_limit: int | None = None


class AdminUpdateUserPasswordRequest(AdminRequestModel):
    password: str


class AdminUpdateUserStatusRequest(AdminRequestModel):
    action: Literal["enable", "disable"]


class AdminAdjustCreditRequest(AdminRequestModel):
    amount: int
    reason: str


class AdminUpdateCreditRuleRequest(AdminRequestModel):
    cost: int = Field(ge=0)


class AdminBulkTerminateTasksRequest(AdminRequestModel):
    task_ids: list[str] = Field(default_factory=list, alias="taskIds")


class AdminCreateInviteRequest(AdminRequestModel):
    role: str = "USER"
    expires_at: str | None = Field(default=None, alias="expiresAt")
