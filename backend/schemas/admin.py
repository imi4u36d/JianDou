from __future__ import annotations
from pydantic import BaseModel
from typing import Optional

class AdminOverviewResponse(BaseModel):
    total_tasks: int = 0
    queued_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0

class AdminTaskBatchResult(BaseModel):
    action: str = ""
    requested_count: int = 0
    succeeded_task_ids: list = []
    failed: list = []

class AdminCreateUserRequest(BaseModel):
    username: str
    display_name: str = ""
    password: str
    role: str = "USER"

class AdminUpdateUserRequest(BaseModel):
    display_name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None

class AdminModelConfigKeyUpdateRequest(BaseModel):
    providers: list = []

class AdminCreateInviteRequest(BaseModel):
    role: str = "USER"
