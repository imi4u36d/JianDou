"""Runtime readiness validation for workflow generation models."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.shared import trim


class WorkflowModelValidator:
    def __init__(self, generation_service_getter: Callable[[], Any]) -> None:
        self._generation_service_getter = generation_service_getter

    async def validate(
        self,
        owner_user_id: int,
        text_model: str,
        image_model: str,
        video_model: str,
    ) -> None:
        generation_service = self._generation_service_getter()
        factory = getattr(generation_service, "_factory", None)
        resolver = getattr(factory, "_config_resolver", None)
        if resolver is None:
            raise ValueError("模型配置服务未初始化，请重启服务后重试。")

        checks = (
            ("文本模型", text_model, "text"),
            ("关键帧模型", image_model, "image"),
            ("视频模型", video_model, "video"),
        )
        for label, model, kind in checks:
            await self._validate_model(resolver, owner_user_id, label, model, kind)

    @staticmethod
    async def _validate_model(resolver: Any, owner_user_id: int, label: str, model: str, kind: str) -> None:
        value = trim(model)
        if not value:
            raise ValueError(f"请先选择{label}。")
        try:
            if kind == "text":
                profile = resolver.resolve_text_profile(value, owner_user_id)
            else:
                profile = resolver.resolve_media_profile(value, kind, owner_user_id)
        except Exception as exc:
            raise ValueError(f"{label}不可用：{value}") from exc

        if not getattr(profile, "provider", ""):
            raise ValueError(f"{label}不可用：{value}")
        if not getattr(profile, "api_key", ""):
            raise ValueError(f"当前用户未设置{label} Key，请先在用户管理中配置 Key。")
        if not getattr(profile, "base_url", ""):
            raise ValueError(f"{label}缺少 base_url，请检查模型配置。")
        if kind == "video" and not getattr(profile, "task_base_url", ""):
            raise ValueError(f"{label}缺少 task_base_url，请检查模型配置。")
        if not getattr(profile, "ready", False):
            raise ValueError(f"{label}配置未就绪，请检查用户 Key 和模型配置。")
