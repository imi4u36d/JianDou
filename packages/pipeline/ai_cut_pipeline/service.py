from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from ai_cut_ai.providers import ModelGateway, ModelRouter
from ai_cut_shared.config import Settings
from ai_cut_db.models import MaterialAsset, SystemLog, Task, TaskModelCall, TaskResult, TaskStatusHistory
from ai_cut_ai.planner import PlannerChain, parse_transcript_cues
from ai_cut_shared.schemas import (
    AdminOverview,
    AdminOverviewCounts,
    AdminTaskActionFailure,
    AdminTaskBatchResult,
    AdminTraceEvent,
    ClipPlan,
    CreateGenerationTaskRequest,
    GenerateCreativePromptRequest,
    GenerateCreativePromptResponse,
    GenerationOptionsResponse,
    GenerationRunRequest,
    GenerationRunResponse,
    GenerationRunStatus,
    MaterialKind,
    MediaType,
    ModelCatalog,
    ProbeTextAnalysisModelRequest,
    ProbeTextAnalysisModelResponse,
    SeeddanceTaskQueryResponse,
    SourceAssetSummary,
    TaskDeleteResult,
    TaskDetail,
    TaskListItem,
    TaskMaterial,
    TaskStatus,
    TaskModelCallRecord,
    TaskModelCallStatus,
    TaskOperationKind,
    TaskOutput as TaskOutputSchema,
    TaskStage,
    TaskStatusHistoryRecord,
    TaskType,
    TraceLevel,
    TaskTraceEvent,
    UploadResponse,
    VideoModelUsageItem,
    VideoModelUsageResponse,
)
from ai_cut_storage.storage import MediaStorage
from ai_cut_pipeline.task_trace import TaskTraceWriter, read_task_trace
from ai_cut_ai.generation_v2.orchestrator import GenerationOrchestrator
from ai_cut_ai.text_generation import (
    GenerationVersionInfo,
    GenerateTextMediaRequest,
    GenerateTextMediaResponse,
    GenerateTextScriptRequest,
    GenerateTextScriptResponse,
    TextGenerationEngine,
)
from ai_cut_shared.utils import extract_llm_text_response, new_id, parse_json_object, truncate_text, utcnow


_CN_TZ = timezone(timedelta(hours=8))


def _iso(value: datetime | None) -> str:
    base = value or utcnow()
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return base.astimezone(_CN_TZ).isoformat()


def _optional_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _iso(value)


def _task_status(value: str) -> str:
    return value


def _task_type(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"", TaskType.GENERATION.value}:
        return TaskType.GENERATION.value
    return normalized


def _task_stage(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == "rendering":
        normalized = TaskStage.RENDER.value
    if normalized in {
        TaskStage.API.value,
        TaskStage.DISPATCH.value,
        TaskStage.PIPELINE.value,
        TaskStage.TASK.value,
        TaskStage.ANALYSIS.value,
        TaskStage.PLANNING.value,
        TaskStage.RENDER.value,
        TaskStage.GENERATION.value,
        TaskStage.SYSTEM.value,
        TaskStage.USAGE.value,
    }:
        return normalized
    return TaskStage.SYSTEM.value


def _task_operation(value: str | None, *, stage: str | None = None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {
        TaskOperationKind.ANALYSIS.value,
        TaskOperationKind.PLANNING.value,
        TaskOperationKind.RENDER.value,
        TaskOperationKind.PIPELINE.value,
        TaskOperationKind.DISPATCH.value,
        TaskOperationKind.GENERATION_VIDEO.value,
        TaskOperationKind.GENERATION_IMAGE.value,
        TaskOperationKind.GENERATION_SCRIPT.value,
        TaskOperationKind.SYSTEM.value,
    }:
        return normalized
    stage_normalized = _task_stage(stage)
    if stage_normalized in {TaskStage.ANALYSIS.value, TaskStage.PLANNING.value, TaskStage.RENDER.value}:
        return stage_normalized
    if stage_normalized in {TaskStage.PIPELINE.value, TaskStage.DISPATCH.value}:
        return stage_normalized
    return TaskOperationKind.SYSTEM.value


def _format_seconds_label(value: float) -> str:
    return f"{max(0.0, float(value)):.1f}s"


INTRO_TEMPLATE_LABELS = {
    "none": "不加片头",
    "cold_open": "冷开场直切",
    "flash_hook": "爆点闪切片头",
    "pressure_build": "情绪压迫片头",
    "hook": "开场冲突钩子",
    "cinematic": "情绪推进片头",
}

OUTRO_TEMPLATE_LABELS = {
    "none": "不加片尾",
    "suspense_hold": "悬念停顿片尾",
    "follow_hook": "追更钩子片尾",
    "question_freeze": "反问定格片尾",
    "brand": "品牌收束片尾",
    "call_to_action": "行动召唤片尾",
}

EDITING_MODE_LABELS = {"drama": "短剧生成"}

DRAMA_PROMPT_APPENDIX = (
    "短剧模式补充：请优先保留高燃卡点、对白完整、冲突升级、反转和情绪爆点，"
    "不要把一句对白或一组动作切断。前后镜头与中间连接点必须连贯，"
    "声音过渡要自然，禁止上一段声音戛然而止后下一段声音立即硬切。"
    "音频仅保留人物对白与环境音，禁止旁白、画外音和解说配音。"
)

_SCRIPT_DURATION_RANGE_RE = re.compile(
    r"(?P<left>\d{1,3}(?:\.\d+)?)\s*(?:-|~|～|—|到)\s*(?P<right>\d{1,3}(?:\.\d+)?)\s*(?:s|秒)",
    re.IGNORECASE,
)
_SCRIPT_DURATION_VALUE_RE = re.compile(
    r"(?<![\d.])(?P<value>\d{1,3}(?:\.\d+)?)\s*(?:s|秒)(?![a-zA-Z])",
    re.IGNORECASE,
)
_SHOT_HEADING_RE = re.compile(
    r"^\s*#{2,4}\s*分镜\s*(?P<index>[0-9一二三四五六七八九十百千两]+)?\s*[·\-：:]*\s*(?P<title>.*)$"
)


def _is_content_policy_blocked_error(message: str | None) -> bool:
    normalized = str(message or "").strip().lower()
    if not normalized:
        return False
    keywords = (
        "datainspectionfailed",
        "inappropriate content",
        "content policy",
        "safety policy",
        "moderation",
        "内容安全",
        "违规",
        "敏感",
        "审核",
    )
    return any(keyword in normalized for keyword in keywords)


def _json_safe(value: object, *, depth: int = 0) -> object:
    if depth >= 10:
        return truncate_text(str(value), 1000) or str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    if is_dataclass(value) and not isinstance(value, type):
        return _json_safe(asdict(value), depth=depth + 1)
    if hasattr(value, "model_dump"):
        try:
            return _json_safe(value.model_dump(mode="json"), depth=depth + 1)  # type: ignore[attr-defined]
        except TypeError:
            try:
                return _json_safe(value.model_dump(), depth=depth + 1)  # type: ignore[attr-defined]
            except Exception:
                pass
        except Exception:
            pass
    if isinstance(value, dict):
        return {
            str(key): _json_safe(item, depth=depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item, depth=depth + 1) for item in value]
    if hasattr(value, "__dict__"):
        try:
            return {
                str(key): _json_safe(item, depth=depth + 1)
                for key, item in vars(value).items()
                if not str(key).startswith("_")
            }
        except Exception:
            pass
    return truncate_text(str(value), 1000) or str(value)


def _json_safe_dict(value: object) -> dict[str, object]:
    payload = _json_safe(value)
    return payload if isinstance(payload, dict) else {}


class TaskPausedError(RuntimeError):
    pass


class TaskTerminatedError(RuntimeError):
    pass


class TaskService:
    def __init__(
        self,
        settings: Settings,
        session_factory: sessionmaker[Session],
        storage: MediaStorage,
        planner: PlannerChain,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.storage = storage
        self.planner = planner
        self.model_router = ModelRouter(settings)
        self.model_gateway = ModelGateway(settings)
        self.text_generator = TextGenerationEngine(settings=settings, storage=storage)
        self.generation_orchestrator = GenerationOrchestrator(
            self.text_generator,
            usage_loader=self.list_video_model_usage,
        )
        self.worker = None

    def set_worker(self, worker) -> None:
        self.worker = worker

    def session(self) -> Session:
        return self.session_factory()

    def _persist_upload(self, file_obj, original_name: str, mime_type: str | None = None) -> UploadResponse:
        stored = self.storage.save_upload(file_obj, original_name, mime_type)
        normalized_mime = str(mime_type or "").strip().lower()
        if normalized_mime.startswith("image/"):
            media_type = "image"
        elif normalized_mime.startswith("text/"):
            media_type = "text"
        elif normalized_mime.startswith("audio/"):
            media_type = "audio"
        else:
            media_type = "video"
        with self.session() as session:
            asset = MaterialAsset(
                id=stored.asset_id,
                task_id="",
                source_material_id="",
                asset_role="source",
                media_type=media_type,
                title=stored.original_file_name,
                original_file_name=stored.original_file_name,
                stored_file_name=stored.stored_file_name,
                file_ext=Path(stored.original_file_name).suffix.lower().lstrip("."),
                storage_provider="local",
                local_path=stored.relative_path,
                public_url=stored.public_url,
                third_party_url="",
                mime_type=normalized_mime,
                size_bytes=stored.size_bytes,
                sha256=stored.sha256,
                has_audio=media_type == "video",
            )
            session.add(asset)
            session.commit()
        return UploadResponse(
            assetId=stored.asset_id,
            fileName=stored.original_file_name,
            fileUrl=stored.public_url,
            sizeBytes=stored.size_bytes,
        )

    def upload_video(self, file_obj, original_name: str, mime_type: str | None = None) -> UploadResponse:
        return self._persist_upload(file_obj, original_name, mime_type)

    def upload_text(self, file_obj, original_name: str, mime_type: str | None = None) -> UploadResponse:
        return self._persist_upload(file_obj, original_name, mime_type or "text/plain")

    def list_generation_options(self) -> GenerationOptionsResponse:
        return self.text_generator.list_options()

    def list_generation_catalog(self) -> ModelCatalog:
        return self.generation_orchestrator.get_catalog()

    def create_generation_run(
        self,
        payload: GenerationRunRequest | dict[str, object],
    ) -> GenerationRunResponse:
        request = (
            payload
            if isinstance(payload, GenerationRunRequest)
            else GenerationRunRequest.model_validate(payload)
        )
        result = self.generation_orchestrator.create_run(request)
        if result.resultVideo is not None:
            metadata = result.resultVideo.metadata if isinstance(result.resultVideo.metadata, dict) else {}
            model_info = result.resultVideo.modelInfo if isinstance(result.resultVideo.modelInfo, dict) else {}
            media_payload = GenerateTextMediaResponse.model_validate(
                {
                    "id": result.id,
                    "kind": "video",
                    "outputUrl": result.resultVideo.outputUrl,
                    "durationSeconds": result.resultVideo.durationSeconds,
                    "width": result.resultVideo.width,
                    "height": result.resultVideo.height,
                    "status": "completed",
                    "metadata": {
                        **metadata,
                        "modelInfo": model_info,
                    },
                }
            )
            self._record_video_model_usage(media_payload)
        return result

    def get_generation_run(self, run_id: str) -> GenerationRunResponse:
        return self.generation_orchestrator.get_run(run_id)

    def list_generation_usage(self) -> VideoModelUsageResponse:
        return self.generation_orchestrator.list_usage()

    def normalize_video_model_key(self, model_name: str) -> str:
        return self.generation_orchestrator.normalize_video_model_key(model_name)

    def list_generation_versions(self) -> list[GenerationVersionInfo]:
        return self.text_generator.list_versions()

    def generate_text_image(
        self,
        payload: GenerateTextMediaRequest | dict[str, object],
    ) -> GenerateTextMediaResponse:
        return self.generation_orchestrator.generate_text_image(payload)

    def generate_text_video(
        self,
        payload: GenerateTextMediaRequest | dict[str, object],
    ) -> GenerateTextMediaResponse:
        result = self.generation_orchestrator.generate_text_video(payload)
        self._record_video_model_usage(result)
        return result

    def generate_text_script(
        self,
        payload: GenerateTextScriptRequest | dict[str, object],
    ) -> GenerateTextScriptResponse:
        return self.generation_orchestrator.generate_text_script(payload)

    def probe_text_analysis_model(
        self,
        payload: ProbeTextAnalysisModelRequest | dict[str, object] | str | None = None,
    ) -> ProbeTextAnalysisModelResponse:
        return self.generation_orchestrator.probe_text_analysis_model(payload)

    def list_video_model_usage(self) -> VideoModelUsageResponse:
        options = self.text_generator.list_options()
        items: list[VideoModelUsageItem] = []
        quota_map = self._resolve_video_model_quota()
        existing = self._load_local_video_model_usage()
        official_usage = self._load_official_video_model_usage(options.videoModels)

        for model in options.videoModels:
            model_key = (getattr(model, "value", "") or "").strip()
            if not model_key:
                continue
            row = existing.get(model_key)
            official = official_usage.get(model_key, {})
            used = float(official.get("used")) if official.get("used") is not None else float(row.get("usedCount", 0) if row is not None else 0.0)
            used_duration = float(row.get("usedDurationSeconds", 0.0)) if row is not None else 0.0
            configured_quota = quota_map.get(model_key)
            quota = (
                float(official.get("quota"))
                if official.get("quota") is not None
                else float(configured_quota)
                if configured_quota is not None
                else float(row.get("quotaCount"))
                if row and row.get("quotaCount") is not None
                else None
            )
            remaining = official.get("remaining")
            if remaining is None and quota is not None and not official:
                remaining = max(0.0, quota - used)
            updated_at = official.get("updatedAt") or (str(row.get("updatedAt") or "") if row is not None else "") or None
            items.append(
                VideoModelUsageItem(
                    model=model_key,
                    label=(getattr(model, "label", "") or model_key).strip(),
                    provider=str(official.get("provider") or self.text_generator.infer_video_provider(model_key)),
                    used=used,
                    unit=str(official.get("unit") or ("次" if not official else "")) or None,
                    remaining=remaining,
                    remainingUnit=str(official.get("remainingUnit") or "") or None,
                    remainingLabel=str(official.get("remainingLabel") or "") or None,
                    quota=quota,
                    usedDurationSeconds=round(used_duration, 3),
                    source=str(official.get("source") or "local-cache"),
                    note=str(official.get("note") or self._build_local_usage_note(model_key)),
                    updatedAt=updated_at,
                )
            )
        return VideoModelUsageResponse(generatedAt=_iso(utcnow()), items=items)

    def _load_local_video_model_usage(self) -> dict[str, dict[str, object]]:
        existing: dict[str, dict[str, object]] = {}
        with self.session() as session:
            rows = session.scalars(
                select(TaskModelCall)
                .where(TaskModelCall.operation == "generation.video")
                .order_by(TaskModelCall.created_at.asc())
            ).all()
            for row in rows:
                model_key = self.text_generator.normalize_video_model_key(row.model_name or row.model_alias)
                if not model_key:
                    continue
                current = existing.setdefault(
                    model_key,
                    {
                        "usedCount": 0.0,
                        "usedDurationSeconds": 0.0,
                        "quotaCount": None,
                        "updatedAt": None,
                    },
                )
                response_payload = row.response_payload_json if isinstance(row.response_payload_json, dict) else {}
                current["usedCount"] = float(current["usedCount"]) + (1.0 if row.success else 0.0)
                current["usedDurationSeconds"] = float(current["usedDurationSeconds"]) + float(
                    response_payload.get("durationSeconds") or 0.0
                )
                if row.updated_at:
                    current["updatedAt"] = _optional_iso(row.updated_at)
        return existing

    def _load_official_video_model_usage(self, video_models: list[object]) -> dict[str, dict[str, object]]:
        result: dict[str, dict[str, object]] = {}
        aliyun_models: list[str] = []
        volc_models: list[str] = []
        for model in video_models:
            model_key = str(getattr(model, "value", "") or "").strip()
            provider = self.text_generator.infer_video_provider(model_key)
            if provider == "volcengine":
                volc_models.append(model_key)
            elif provider == "aliyun-bailian":
                aliyun_models.append(model_key)

        if aliyun_models and self._has_aliyun_billing_credentials():
            try:
                result.update(self._fetch_aliyun_official_usage(aliyun_models))
            except Exception:
                pass
        if volc_models and self._has_volcengine_billing_credentials():
            try:
                result.update(self._fetch_volcengine_official_usage(volc_models))
            except Exception:
                pass
        return result

    def _has_aliyun_billing_credentials(self) -> bool:
        return bool(
            self.settings.model.aliyun_billing_access_key_id.strip()
            and self.settings.model.aliyun_billing_access_key_secret.strip()
        )

    def _has_volcengine_billing_credentials(self) -> bool:
        return bool(
            self.settings.model.volcengine_billing_access_key_id.strip()
            and self.settings.model.volcengine_billing_access_key_secret.strip()
        )

    def _build_local_usage_note(self, model_key: str) -> str:
        provider = self.text_generation_provider_for_usage(model_key)
        if provider == "volcengine" and not self._has_volcengine_billing_credentials():
            return "未配置火山费用中心 AK/SK，当前显示本地累计统计。"
        if provider == "aliyun-bailian" and not self._has_aliyun_billing_credentials():
            return "未配置阿里云账单 AK/SK，当前显示本地累计统计。"
        return "官方账单暂未识别到该模型，当前回退本地累计统计。"

    def text_generation_provider_for_usage(self, model_key: str) -> str:
        return self.text_generator.infer_video_provider(model_key)

    def _fetch_aliyun_official_usage(self, model_keys: list[str]) -> dict[str, dict[str, object]]:
        from alibabacloud_bssopenapi20171214.client import Client as BssClient
        from alibabacloud_bssopenapi20171214 import models as bss_models
        from alibabacloud_tea_openapi import models as open_api_models

        config = open_api_models.Config(
            access_key_id=self.settings.model.aliyun_billing_access_key_id,
            access_key_secret=self.settings.model.aliyun_billing_access_key_secret,
            endpoint="business.aliyuncs.com",
        )
        client = BssClient(config)

        balance_response = client.query_account_balance()
        balance_payload = balance_response.body.to_map() if hasattr(balance_response.body, "to_map") else {}
        balance_data = balance_payload.get("Data") or balance_payload.get("data") or {}
        available_balance = self._parse_float(balance_data.get("AvailableAmount") or balance_data.get("available_amount"))
        currency = str(balance_data.get("Currency") or balance_data.get("currency") or "CNY")

        bill_period = datetime.now().strftime("%Y-%m")
        page_num = 1
        aggregated: dict[str, dict[str, object]] = {}
        normalized_targets = {self.text_generator.normalize_video_model_key(item) for item in model_keys}
        while True:
            request = bss_models.QueryInstanceBillRequest(
                billing_cycle=bill_period,
                page_num=page_num,
                page_size=100,
                is_hide_zero_charge=True,
            )
            response = client.query_instance_bill(request)
            payload = response.body.to_map() if hasattr(response.body, "to_map") else {}
            data = payload.get("Data") or payload.get("data") or {}
            items_block = data.get("Items") or data.get("items") or {}
            rows = items_block.get("Item") or items_block.get("item") or []
            if not isinstance(rows, list):
                rows = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                model_key = self._match_aliyun_model_key(row, normalized_targets)
                if not model_key:
                    continue
                usage_value = self._parse_float(row.get("Usage") or row.get("usage"))
                if usage_value is None:
                    continue
                current = aggregated.setdefault(
                    model_key,
                    {
                        "model": model_key,
                        "provider": "aliyun-bailian",
                        "used": 0.0,
                        "unit": str(row.get("UsageUnit") or row.get("usage_unit") or "次"),
                        "remaining": available_balance,
                        "remainingUnit": currency,
                        "remainingLabel": "余额",
                        "source": "official-billing",
                        "note": "已用量来自阿里云官方账单，剩余列显示阿里云账号可用余额。",
                        "updatedAt": _iso(utcnow()),
                    },
                )
                current["used"] = float(current["used"]) + usage_value

            total_count = int(data.get("TotalCount") or data.get("total_count") or 0)
            page_size = int(data.get("PageSize") or data.get("page_size") or 100)
            if page_num * page_size >= total_count or not rows:
                break
            page_num += 1
        return aggregated

    def _match_aliyun_model_key(self, row: dict[str, object], model_keys: set[str]) -> str:
        text = " ".join(
            str(row.get(key) or "")
            for key in (
                "InstanceId",
                "instance_id",
                "InstanceSpec",
                "instance_spec",
                "ProductDetail",
                "product_detail",
                "BillingItem",
                "billing_item",
                "NickName",
                "nick_name",
                "Item",
                "item",
                "ProductName",
                "product_name",
            )
        ).lower()
        text = re.sub(r"\s+", " ", text)
        for model_key in sorted(model_keys, key=len, reverse=True):
            if model_key and model_key in text:
                return model_key
        aliases = {
            "qwen-vl-plus-latest": "qwen-vl",
            "qwen-vl-max-latest": "qwen-vl",
            "wan2.6-t2v-plus": "wan2.6-t2v",
            "wan2.6-t2v-turbo": "wan2.6-t2v",
        }
        for alias, model_key in aliases.items():
            if model_key in model_keys and alias in text:
                return model_key
        return ""

    def _fetch_volcengine_official_usage(self, model_keys: list[str]) -> dict[str, dict[str, object]]:
        from volcengine.ApiInfo import ApiInfo
        from volcengine.billing.BillingService import BillingService

        service = BillingService()
        service.set_ak(self.settings.model.volcengine_billing_access_key_id)
        service.set_sk(self.settings.model.volcengine_billing_access_key_secret)
        service.api_info["QueryBalanceAcct"] = ApiInfo("GET", "/", {"Action": "QueryBalanceAcct", "Version": "2022-01-01"}, {}, {})

        balance_raw = service.get("QueryBalanceAcct", {})
        balance_payload = json.loads(balance_raw)
        balance_result = balance_payload.get("Result") or {}
        available_balance = self._parse_float(balance_result.get("AvailableBalance"))

        bill_period = datetime.now().strftime("%Y-%m")
        offset = 0
        limit = 100
        aggregated: dict[str, dict[str, object]] = {}
        while True:
            payload = service.list_bill_detail(
                {},
                {
                    "Offset": offset,
                    "Limit": limit,
                    "BillPeriod": bill_period,
                    "GroupPeriod": 2,
                    "GroupTerm": 1,
                    "IgnoreZero": 1,
                    "NeedRecordNum": 1,
                },
            )
            result = payload.get("Result") or {}
            rows = result.get("List") or []
            if not isinstance(rows, list):
                rows = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                model_key = self._match_volcengine_model_key(row, model_keys)
                if not model_key:
                    continue
                usage_value = (
                    self._parse_float(row.get("Count"))
                    or self._parse_float(row.get("UseDuration"))
                    or self._parse_float(row.get("DeductionCount"))
                )
                if usage_value is None:
                    continue
                unit = str(row.get("Unit") or row.get("UseDurationUnit") or "次")
                current = aggregated.setdefault(
                    model_key,
                    {
                        "model": model_key,
                        "provider": "volcengine",
                        "used": 0.0,
                        "unit": unit,
                        "remaining": available_balance,
                        "remainingUnit": "CNY",
                        "remainingLabel": "余额",
                        "source": "official-billing",
                        "note": "已用量来自火山费用中心官方账单，剩余列显示火山账号可用余额。",
                        "updatedAt": _iso(utcnow()),
                    },
                )
                current["used"] = float(current["used"]) + usage_value
            total = int(result.get("Total") or 0)
            offset += limit
            if offset >= total or not rows:
                break
        return aggregated

    def _match_volcengine_model_key(self, row: dict[str, object], model_keys: list[str]) -> str:
        text = " ".join(
            str(row.get(key) or "")
            for key in (
                "Product",
                "ProductZh",
                "InstanceName",
                "InstanceNo",
                "ConfigName",
                "ExpandField",
                "ProjectDisplayName",
            )
        ).lower()
        if "seeddance-1.5-pro" in model_keys and any(keyword in text for keyword in ("seedance", "seeddance", "火山", "豆包")):
            return "seeddance-1.5-pro"
        return ""

    def _parse_float(self, value: object) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        if not text:
            return None
        try:
            return float(text)
        except Exception:
            return None

    def _default_generation_duration_seconds(self) -> int:
        try:
            catalog = self.generation_orchestrator.get_catalog()
            raw_value = getattr(catalog, "defaultVideoDurationSeconds", None)
            default_duration = int(float(raw_value)) if raw_value not in {None, ""} else 0
        except Exception:
            default_duration = 0
        return max(1, min(120, default_duration or 5))

    def _resolve_keyframe_dimensions(self, aspect_ratio: str | None) -> tuple[int, int]:
        normalized = str(aspect_ratio or "").strip()
        if normalized == "16:9":
            return 1344, 768
        if normalized == "9:16":
            return 768, 1344
        return 1024, 1024

    def _build_keyframe_prompt(self, *, prompt: str, analysis_script_text: str) -> str:
        normalized_prompt = truncate_text(str(prompt or "").strip(), 1800) or "短剧关键帧"
        normalized_script = truncate_text(str(analysis_script_text or "").strip(), 1600) or ""
        parts = [
            "请生成短剧关键帧海报风格画面。",
            "要求：单帧构图明确、主体突出、光影有戏剧张力、适合作为视频封面。",
            f"创意提示词：{normalized_prompt}",
        ]
        if normalized_script:
            parts.append(f"分镜参考：{normalized_script}")
        return truncate_text("\n\n".join(parts), 4500) or normalized_prompt

    def _infer_image_provider(self, model_name: str | None) -> str:
        try:
            target = self.model_router.resolve(model_name, capability="image_generation", kind="image")
            return target.provider_name or "unknown"
        except Exception:
            normalized = str(model_name or "").strip().lower()
            if "seedream" in normalized:
                return "volcengine"
            return "unknown"

    def _extension_from_mime_type(self, mime_type: str | None) -> str:
        normalized = str(mime_type or "").strip().lower()
        if "png" in normalized:
            return "png"
        if "jpeg" in normalized or "jpg" in normalized:
            return "jpg"
        if "webp" in normalized:
            return "webp"
        if "svg" in normalized:
            return "svg"
        return "png"

    def _generate_planning_keyframe(
        self,
        *,
        task_id: str,
        task_title: str,
        aspect_ratio: str,
        prompt: str,
        analysis_script_text: str,
        text_model: str | None,
        context_payload: dict[str, object],
    ) -> None:
        requested_image_model = str(
            context_payload.get("imageModel")
            or context_payload.get("imageProviderModel")
            or self.settings.model.defaults.image_generation
            or ""
        ).strip()
        keyframe_prompt = self._build_keyframe_prompt(
            prompt=prompt,
            analysis_script_text=analysis_script_text,
        )
        width, height = self._resolve_keyframe_dimensions(aspect_ratio)
        provider_guess = self._infer_image_provider(requested_image_model)

        self._trace(
            task_id,
            "planning",
            "planning.keyframe_started",
            "开始执行关键帧文生图。",
            {
                "model": requested_image_model,
                "provider": provider_guess,
                "width": width,
                "height": height,
            },
        )

        input_payload: dict[str, object] = {
            "prompt": keyframe_prompt,
            "width": width,
            "height": height,
            "extras": {
                "purpose": "planning_keyframe",
                "taskId": task_id,
            },
        }
        model_payload: dict[str, object] = {}
        if text_model:
            model_payload["textAnalysisModel"] = text_model
        if requested_image_model:
            model_payload["providerModel"] = requested_image_model

        run_request = GenerationRunRequest(
            kind="image",
            input=input_payload,
            model=model_payload,
            options={},
        )
        run_response = self.generation_orchestrator.create_run(run_request)
        response_payload = _json_safe_dict(run_response.model_dump())

        if run_response.status != GenerationRunStatus.SUCCEEDED or run_response.resultImage is None:
            error_message = run_response.error.message if run_response.error else "keyframe generation run failed"
            error_code = run_response.error.code if run_response.error else "generation_failed"
            http_status = 0
            if run_response.error is not None:
                http_status = int(
                    getattr(run_response.error, "statusCode", 0)
                    or getattr(run_response.error, "httpStatus", 0)
                    or 0
                )
            self._record_task_model_call(
                task_id=task_id,
                stage="planning",
                operation="generation.image",
                provider=provider_guess,
                provider_model=requested_image_model,
                requested_model=requested_image_model,
                resolved_model="",
                request_payload=_json_safe_dict(run_request.model_dump()),
                response_payload=response_payload,
                success=False,
                http_status=http_status,
                error_code=str(error_code or "generation_failed"),
                error_message=error_message,
            )
            context_payload["keyframeStatus"] = "failed"
            context_payload["keyframeRunId"] = run_response.id
            context_payload.pop("keyframeRemoteSourceUrl", None)
            context_payload["keyframeError"] = truncate_text(error_message, 500) or error_message
            self.storage.save_task_context(task_id, context_payload)
            self._trace(
                task_id,
                "planning",
                "planning.keyframe_failed",
                "关键帧文生图失败，已降级继续后续流程。",
                {
                    "run_id": run_response.id,
                    "model": requested_image_model,
                    "provider": provider_guess,
                    "error": error_message,
                },
                "WARN",
            )
            return

        result = run_response.resultImage
        output_url = str(result.outputUrl or "").strip()
        if not output_url:
            error_message = "keyframe generation succeeded but outputUrl is empty"
            self._record_task_model_call(
                task_id=task_id,
                stage="planning",
                operation="generation.image",
                provider=provider_guess,
                provider_model=requested_image_model,
                requested_model=requested_image_model,
                resolved_model="",
                request_payload=_json_safe_dict(run_request.model_dump()),
                response_payload=response_payload,
                success=False,
                http_status=200,
                error_code="empty_output_url",
                error_message=error_message,
            )
            context_payload["keyframeStatus"] = "failed"
            context_payload["keyframeRunId"] = run_response.id
            context_payload.pop("keyframeRemoteSourceUrl", None)
            context_payload["keyframeError"] = error_message
            self.storage.save_task_context(task_id, context_payload)
            self._trace(
                task_id,
                "planning",
                "planning.keyframe_failed",
                "关键帧文生图结果缺少输出地址，已降级继续后续流程。",
                {
                    "run_id": run_response.id,
                    "model": requested_image_model,
                    "provider": provider_guess,
                    "error": error_message,
                },
                "WARN",
            )
            return

        metadata = result.metadata if isinstance(result.metadata, dict) else {}
        model_info = result.modelInfo if isinstance(result.modelInfo, dict) else {}
        remote_source_url = str(metadata.get("remoteSourceUrl") or "").strip()
        provider = str(
            model_info.get("provider")
            or metadata.get("provider")
            or provider_guess
        ).strip() or provider_guess
        resolved_model = str(
            model_info.get("resolvedModel")
            or model_info.get("modelName")
            or model_info.get("providerModel")
            or metadata.get("providerModel")
            or requested_image_model
            or self.settings.model.defaults.image_generation
            or ""
        ).strip()
        mime_type = str(
            getattr(result, "mimeType", "")
            or metadata.get("mimeType")
            or "image/png"
        ).strip() or "image/png"
        width_value = max(0, int(result.width or width or 0))
        height_value = max(0, int(result.height or height or 0))
        size_bytes = 0
        try:
            size_bytes = max(0, int(float(metadata.get("byteSize") or 0)))
        except Exception:
            size_bytes = 0

        model_call_id = self._record_task_model_call(
            task_id=task_id,
            stage="planning",
            operation="generation.image",
            provider=provider,
            provider_model=requested_image_model,
            requested_model=requested_image_model,
            resolved_model=resolved_model,
            request_payload=_json_safe_dict(run_request.model_dump()),
            response_payload=response_payload,
            success=True,
            http_status=200,
            input_tokens=int(model_info.get("inputTokens") or 0),
            output_tokens=int(model_info.get("outputTokens") or 0),
        )
        extension = self._extension_from_mime_type(mime_type)
        with self.session() as session:
            session.add(
                MaterialAsset(
                    id=new_id("asset"),
                    task_id=task_id,
                    source_task_id="",
                    source_material_id="",
                    asset_role="intermediate",
                    media_type="image",
                    title=f"{task_title} 关键帧",
                    origin_provider=provider,
                    origin_model=resolved_model,
                    remote_task_id=run_response.id,
                    remote_asset_id="",
                    original_file_name=f"{task_id}_keyframe.{extension}",
                    stored_file_name="",
                    file_ext=extension,
                    storage_provider="remote",
                    mime_type=mime_type,
                    size_bytes=size_bytes,
                    sha256="",
                    duration_seconds=0.0,
                    width=width_value,
                    height=height_value,
                    has_audio=False,
                    local_path="",
                    local_file_path="",
                    public_url=output_url,
                    third_party_url=output_url,
                    remote_url=output_url,
                    metadata_json=_json_safe_dict({
                        "runId": run_response.id,
                        "modelCallId": model_call_id,
                        "kind": "keyframe",
                        "callChain": result.callChain,
                        "modelInfo": model_info,
                    }),
                )
            )
            session.commit()

        context_payload["keyframeStatus"] = "succeeded"
        context_payload["keyframeRunId"] = run_response.id
        context_payload["keyframeOutputUrl"] = output_url
        if remote_source_url:
            context_payload["keyframeRemoteSourceUrl"] = remote_source_url
        else:
            context_payload.pop("keyframeRemoteSourceUrl", None)
        context_payload["keyframeModel"] = resolved_model
        context_payload["keyframeProvider"] = provider
        context_payload.pop("keyframeError", None)
        self.storage.save_task_context(task_id, context_payload)
        self._trace(
            task_id,
            "planning",
            "planning.keyframe_completed",
            "关键帧文生图完成。",
            {
                "run_id": run_response.id,
                "model": resolved_model or requested_image_model,
                "provider": provider,
                "output_url": output_url,
                "width": width_value,
                "height": height_value,
            },
        )

    def _extract_script_duration_values(self, script_text: str) -> list[float]:
        normalized_text = str(script_text or "").strip()
        if not normalized_text:
            return []

        values: list[float] = []
        text_without_ranges = normalized_text
        for match in _SCRIPT_DURATION_RANGE_RE.finditer(normalized_text):
            try:
                left = float(match.group("left"))
                right = float(match.group("right"))
            except Exception:
                continue
            candidate = (left + right) / 2.0
            if 0.2 <= candidate <= 120:
                values.append(candidate)
            text_without_ranges = text_without_ranges.replace(match.group(0), " ")

        for match in _SCRIPT_DURATION_VALUE_RE.finditer(text_without_ranges):
            try:
                candidate = float(match.group("value"))
            except Exception:
                continue
            if 0.2 <= candidate <= 120:
                values.append(candidate)
        return values

    def _resolve_auto_duration_seconds(self, script_text: str, *, fallback_seconds: int) -> tuple[int, int]:
        fallback = max(1, min(120, int(fallback_seconds or 0) or self._default_generation_duration_seconds()))
        values = self._extract_script_duration_values(script_text)
        if not values:
            return fallback, 0
        average_seconds = int(round(sum(values) / max(1, len(values))))
        if average_seconds <= 0:
            return fallback, 0
        resolved = max(1, min(120, average_seconds))
        return resolved, len(values)

    def _parse_duration_range_hint(self, text: str | None) -> tuple[int, int] | None:
        normalized_text = str(text or "").strip()
        if not normalized_text:
            return None

        range_match = _SCRIPT_DURATION_RANGE_RE.search(normalized_text)
        if range_match:
            try:
                left = float(range_match.group("left"))
                right = float(range_match.group("right"))
            except Exception:
                return None
            low = max(1, min(120, int(round(min(left, right)))))
            high = max(low, min(120, int(round(max(left, right)))))
            return low, high

        value_match = _SCRIPT_DURATION_VALUE_RE.search(normalized_text)
        if value_match:
            try:
                value = float(value_match.group("value"))
            except Exception:
                return None
            center = max(1, min(120, int(round(value))))
            low = max(1, center - 1)
            high = min(120, center + 1)
            if high <= low:
                high = min(120, low + 1)
            return low, max(low, high)
        return None

    def _extract_storyboard_shot_duration_ranges(self, analysis_script_text: str) -> list[tuple[int, int]]:
        normalized_text = str(analysis_script_text or "").strip()
        if not normalized_text:
            return []
        lines = [line.rstrip() for line in normalized_text.splitlines()]
        ranges: list[tuple[int, int]] = []

        for line in lines:
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if len(cells) < 2:
                continue
            if all(re.fullmatch(r"[:\-\s]*", cell or "") for cell in cells):
                continue
            first = cells[0]
            if not first:
                continue
            if "镜号" in first or "shot" in first.lower():
                continue
            duration_cell = cells[6] if len(cells) > 6 else cells[-1]
            parsed = self._parse_duration_range_hint(duration_cell)
            if parsed is not None:
                ranges.append(parsed)

        if ranges:
            return ranges

        fallback_ranges: list[tuple[int, int]] = []
        for match in _SCRIPT_DURATION_RANGE_RE.finditer(normalized_text):
            parsed = self._parse_duration_range_hint(match.group(0))
            if parsed is not None:
                fallback_ranges.append(parsed)
        return fallback_ranges

    def _resolve_video_model_duration_constraints(self, video_model: str | None) -> tuple[int, int, bool]:
        normalized_model = self.normalize_video_model_key(video_model or "")
        constraints = self.text_generator.get_model_constraints()
        for item in constraints:
            if str(item.get("mediaKind") or "").strip().lower() != "video":
                continue
            model_key = self.normalize_video_model_key(str(item.get("model") or ""))
            if model_key != normalized_model:
                continue
            min_duration = max(1, min(120, int(item.get("minDurationSeconds") or self._default_generation_duration_seconds())))
            max_duration = max(min_duration, min(120, int(item.get("maxDurationSeconds") or min_duration)))
            return min_duration, max_duration, min_duration == max_duration
        fallback = self._default_generation_duration_seconds()
        safe_fallback = max(1, min(120, int(fallback)))
        return safe_fallback, safe_fallback, True

    def _build_clip_duration_plan(
        self,
        *,
        clip_count: int,
        default_min_duration: int,
        default_max_duration: int,
        shot_duration_ranges: list[tuple[int, int]],
    ) -> list[tuple[int, int, int]]:
        normalized_count = max(1, int(clip_count or 1))
        global_min = max(1, min(120, int(default_min_duration or 1)))
        global_max = max(global_min, min(120, int(default_max_duration or global_min)))
        plan: list[tuple[int, int, int]] = []
        for index in range(normalized_count):
            if index < len(shot_duration_ranges):
                clip_min_raw, clip_max_raw = shot_duration_ranges[index]
            else:
                clip_min_raw, clip_max_raw = global_min, global_max
            clip_min = max(global_min, min(global_max, int(clip_min_raw)))
            clip_max = max(global_min, min(global_max, int(clip_max_raw)))
            if clip_min > clip_max:
                clip_min, clip_max = global_min, global_max
            clip_target = max(clip_min, min(clip_max, int(round((clip_min + clip_max) / 2))))
            plan.append((clip_target, clip_min, clip_max))
        return plan

    def _strip_narration_voiceover_text(self, text: str | None) -> str:
        normalized = str(text or "").strip()
        if not normalized:
            return ""
        lowered = normalized.lower()
        if "旁白" not in normalized and "画外音" not in normalized and "解说" not in normalized and "narration" not in lowered and "voiceover" not in lowered and "voice over" not in lowered:
            return normalized
        cleaned = re.sub(
            r"[（(]\s*(?:旁白|画外音|解说|narration|voice\s*over|voiceover)\s*[)）]\s*[:：]?\s*",
            "",
            normalized,
            flags=re.IGNORECASE,
        )
        segments = re.split(r"[；;。!！?？\n]+", cleaned)
        kept: list[str] = []
        for segment in segments:
            candidate = segment.strip()
            if not candidate:
                continue
            lowered_candidate = candidate.lower()
            if "旁白" in candidate or "画外音" in candidate or "解说" in candidate or "narration" in lowered_candidate or "voiceover" in lowered_candidate or "voice over" in lowered_candidate:
                continue
            kept.append(candidate)
        merged = "；".join(kept).strip("，,；;。 ")
        return merged

    def _extract_storyboard_shot_prompts(self, analysis_script_text: str) -> list[str]:
        max_outputs = max(1, int(self.settings.pipeline.max_output_count or 1))
        normalized = str(analysis_script_text or "").strip()
        if not normalized:
            return []
        lines = [line.rstrip() for line in normalized.splitlines()]
        shot_prompts: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if len(cells) < 4:
                continue
            if all(re.fullmatch(r"[:\-\s]*", cell or "") for cell in cells):
                continue
            first = cells[0]
            if not first:
                continue
            if "镜号" in first or "shot" in first.lower():
                continue
            shot_index = re.sub(r"[^0-9一二三四五六七八九十百千两]", "", first) or str(len(shot_prompts) + 1)
            scene = cells[1] if len(cells) > 1 else ""
            camera = cells[2] if len(cells) > 2 else ""
            visual = cells[3] if len(cells) > 3 else ""
            dialogue = self._strip_narration_voiceover_text(cells[4] if len(cells) > 4 else "")
            audio = cells[5] if len(cells) > 5 else ""
            duration_hint = cells[6] if len(cells) > 6 else ""
            parts = [f"镜头编号：{shot_index}"]
            if scene:
                parts.append(f"剧情节点：{scene}")
            if camera:
                parts.append(f"镜头语言：{camera}")
            if visual:
                parts.append(f"画面描述：{visual}")
            if dialogue:
                parts.append(f"人物对白：{dialogue}")
            if audio:
                parts.append(f"声音设计：{audio}")
            if duration_hint:
                parts.append(f"建议时长：{duration_hint}")
            prompt = "；".join(parts)
            if prompt:
                shot_prompts.append(truncate_text(prompt, 420) or prompt)
            if len(shot_prompts) >= max_outputs:
                return shot_prompts

        if shot_prompts:
            return shot_prompts

        current_title = ""
        current_lines: list[str] = []

        def flush_heading_shot() -> None:
            nonlocal current_title, current_lines
            if len(shot_prompts) >= max_outputs:
                current_title = ""
                current_lines = []
                return
            title = current_title.strip()
            body = " ".join(item.strip("-* \t") for item in current_lines if item.strip())
            body = self._strip_narration_voiceover_text(body)
            if title and body:
                merged = f"剧情节点：{title}；画面描述：{body}"
            elif title:
                merged = f"剧情节点：{title}"
            else:
                merged = body
            merged = merged.strip()
            if merged:
                shot_prompts.append(truncate_text(merged, 420) or merged)
            current_title = ""
            current_lines = []

        for line in lines:
            stripped = line.strip()
            match = _SHOT_HEADING_RE.match(stripped)
            if match:
                flush_heading_shot()
                current_title = str(match.group("title") or "").strip()
                continue
            if current_title:
                current_lines.append(line)

        flush_heading_shot()
        return shot_prompts[:max_outputs]

    def _build_sequential_clip_prompts(
        self,
        *,
        base_prompt: str,
        analysis_script_text: str,
        fallback_count: int,
    ) -> list[str]:
        max_outputs = max(1, int(self.settings.pipeline.max_output_count or 1))
        requested_count = max(1, min(max_outputs, int(fallback_count or 1)))
        shot_prompts = self._extract_storyboard_shot_prompts(analysis_script_text)
        audio_rule = "音频要求：保留人物对白与环境音，禁止旁白、画外音、解说配音。"
        if shot_prompts:
            total = len(shot_prompts)
            prompts: list[str] = []
            for index, shot_prompt in enumerate(shot_prompts, start=1):
                continuity_hint = "承接上一镜动作与情绪，衔接自然。" if index > 1 else "建立场景与人物关系。"
                composed = (
                    f"{base_prompt}\n\n"
                    f"按剧情顺序仅生成第 {index}/{total} 镜，不要跨镜头合并。\n"
                    f"{shot_prompt}\n"
                    f"{continuity_hint}\n"
                    f"{audio_rule}"
                )
                prompts.append(truncate_text(composed, 6200) or composed)
            return prompts

        prompts: list[str] = []
        for index in range(1, requested_count + 1):
            continuity_hint = "承接上一镜动作与情绪，衔接自然。" if index > 1 else "建立场景与人物关系。"
            composed = (
                f"{base_prompt}\n\n"
                f"按剧情顺序仅生成第 {index}/{requested_count} 镜，不要跨镜头合并。\n"
                f"{continuity_hint}\n"
                f"{audio_rule}"
            )
            prompts.append(truncate_text(composed, 6200) or composed)
        return prompts

    def _record_video_model_usage(self, result: GenerateTextMediaResponse) -> None:
        metadata = result.metadata if isinstance(result.metadata, dict) else {}
        model_info = metadata.get("modelInfo") if isinstance(metadata.get("modelInfo"), dict) else {}
        raw_model_key = str(
            metadata.get("selectedProviderModel")
            or model_info.get("providerModel")
            or metadata.get("providerModel")
            or ""
        ).strip().lower()
        model_key = self.text_generator.normalize_video_model_key(raw_model_key)
        if not model_key:
            return
        provider = str(model_info.get("provider") or metadata.get("provider") or "").strip() or self.text_generator.infer_video_provider(model_key)
        duration_seconds = float(result.durationSeconds or metadata.get("durationSeconds") or 0.0)
        request_payload = {
            "prompt": str(result.prompt or ""),
            "kind": "video",
            "providerModel": raw_model_key,
            "metadata": metadata,
        }
        response_payload = {
            "outputUrl": str(result.outputUrl or ""),
            "durationSeconds": duration_seconds,
            "width": result.width,
            "height": result.height,
            "metadata": metadata,
        }
        request_payload = _json_safe_dict(request_payload)
        response_payload = _json_safe_dict(response_payload)
        with self.session() as session:
            session.add(
                TaskModelCall(
                    id=new_id("mdlcall"),
                    task_id="",
                    stage=TaskStage.GENERATION.value,
                    operation="generation.video",
                    provider=provider,
                    model_name=model_key,
                    model_alias=str(model_info.get("resolvedModel") or model_info.get("requestedModel") or ""),
                    endpoint_host=str(model_info.get("endpointHost") or ""),
                    request_id="",
                    request_payload_json=request_payload,
                    response_payload_json=response_payload,
                    response_status_code=200,
                    duration_ms=0,
                    input_tokens=0,
                    output_tokens=0,
                    success=True,
                    error_code="",
                    error_message="",
                    started_at=utcnow(),
                    finished_at=utcnow(),
                )
            )
            session.commit()

    def _resolve_video_model_quota(self) -> dict[str, int]:
        raw = (self.settings.model.video_model_usage_quota or "").strip()
        if not raw:
            return {}
        try:
            payload = json.loads(raw)
        except Exception:
            return {}
        if not isinstance(payload, dict):
            return {}
        result: dict[str, int] = {}
        for key, value in payload.items():
            raw_key = str(key).strip().lower()
            model_key = self.text_generator.normalize_video_model_key(raw_key)
            if not model_key:
                continue
            try:
                quota = int(value)
            except Exception:
                continue
            if quota < 0:
                continue
            result[model_key] = quota
        return result

    def _editing_mode_label(self, editing_mode: str | None) -> str:
        return EDITING_MODE_LABELS["drama"]

    def generate_creative_prompt(self, payload: GenerateCreativePromptRequest) -> GenerateCreativePromptResponse:
        if payload.minDurationSeconds > payload.maxDurationSeconds:
            raise ValueError("minDurationSeconds must be less than or equal to maxDurationSeconds")
        text_model = self.model_router.resolve(capability="creative_prompt", kind="text")
        model_name = text_model.model_name
        generated = self._call_creative_prompt_model(model_name, payload)
        if not generated:
            raise RuntimeError("creative prompt model returned empty prompt")
        return GenerateCreativePromptResponse(
            prompt=self._append_editing_mode_prompt(
                generated,
                source_count=len(payload.sourceFileNames),
                source_names=payload.sourceFileNames,
            ),
            source=model_name,
        )

    def _call_creative_prompt_model(
        self,
        model_name: str,
        payload: GenerateCreativePromptRequest,
    ) -> str:
        transcript_excerpt = truncate_text((payload.transcriptText or "").strip(), 1400) or ""
        mode_label = self._editing_mode_label(payload.editingMode)
        mode_hint = (
            "短剧模式强调高燃卡点、对白完整、冲突升级和反转情绪，"
            "并要求镜头连接点与声音转场自然连续，仅保留人物对白和环境音，去掉旁白配音。"
        )
        request_prompt = (
            "你是视频混剪策划，请只输出 JSON，不要解释。\n"
            "目标：生成一段适合视频剪辑规划的大模型提示词，给后续剪辑模型使用。\n"
            "这段提示词必须是中文，长度控制在 70 到 140 个字。"
            f"当前编辑模式：{mode_label}。\n"
            f"{mode_hint}\n"
            "不要重复参数，不要写成说明文，不要出现序号。\n"
            f"任务标题：{payload.title}\n"
            f"画幅：{payload.aspectRatio}\n"
            f"时长区间：{payload.minDurationSeconds}-{payload.maxDurationSeconds} 秒\n"
            f"片头模板：{INTRO_TEMPLATE_LABELS.get(payload.introTemplate, payload.introTemplate)}\n"
            f"片尾模板：{OUTRO_TEMPLATE_LABELS.get(payload.outroTemplate, payload.outroTemplate)}\n"
            f"素材文件：{json.dumps(getattr(payload, 'sourceFileNames', [])[:6], ensure_ascii=False)}\n"
            "编辑模式：drama\n"
            f"字幕/台词摘录：{json.dumps(transcript_excerpt, ensure_ascii=False)}\n"
            '输出格式：{"prompt":"..."}'
        )
        _, result = self.model_gateway.invoke_text(
            model_name=model_name,
            capability="creative_prompt",
            system_prompt=self.settings.prompts.creative_prompt_generator_json_only,
            user_prompt=request_prompt,
            temperature=min(0.55, max(0.18, self.settings.model.temperature + 0.08)),
            max_tokens=min(500, self.settings.model.max_tokens),
            enable_thinking=False,
        )
        content = extract_llm_text_response(result.payload, result.raw_text)
        parsed_prompt, _ = parse_json_object(content or result.raw_text)
        prompt = str(parsed_prompt.get("prompt", "")).strip()
        return truncate_text(prompt, 180) or ""

    def _build_fallback_creative_prompt(self, payload: GenerateCreativePromptRequest) -> str:
        duration_label = f"{payload.minDurationSeconds}-{payload.maxDurationSeconds}秒"
        intro = INTRO_TEMPLATE_LABELS.get(payload.introTemplate, payload.introTemplate)
        outro = OUTRO_TEMPLATE_LABELS.get(payload.outroTemplate, payload.outroTemplate)
        if payload.transcriptText and "-->" in payload.transcriptText:
            semantic_hint = "优先贴近字幕时间轴，完整保留关键对白和情绪爆点"
        elif payload.transcriptText and payload.transcriptText.strip():
            semantic_hint = "优先抓住对白冲突、反转信息和情绪升级"
        else:
            semantic_hint = "优先寻找高燃冲突、表情反转和动作爆点"
        return (
            f"围绕《{payload.title}》做短剧生成，目标时长{duration_label}，"
            f"{semantic_hint}，开头采用{intro}，结尾落在{outro}，"
            "不要切断对白或连续动作，最后一拍要有明确落点，"
            "相邻片段声音要平滑衔接，避免戛然而止与硬切入，"
            "只保留人物对白与环境音，不要旁白和画外音解说。"
        )

    def _append_editing_mode_prompt(
        self,
        prompt: str | None,
        *,
        source_count: int | None = None,
        source_names: list[str] | None = None,
    ) -> str:
        base = (prompt or "").strip()
        appendix = DRAMA_PROMPT_APPENDIX
        if base and DRAMA_PROMPT_APPENDIX in base:
            return base
        details: list[str] = []
        if source_count is not None and source_count > 1:
            details.append(f"当前共有 {source_count} 个素材")
        if source_names:
            preview = "、".join([name for name in source_names[:3] if name])
            if preview:
                details.append(f"素材示例：{preview}")
        if details:
            appendix = f"{appendix} {'；'.join(details)}。"
        if base:
            return f"{base}\n{appendix}"
        return appendix

    def _resolve_task_creative_prompt(self, creative_prompt: str | None) -> str:
        normalized = str(creative_prompt or "").strip()
        if normalized:
            return normalized
        return self._append_editing_mode_prompt(None)

    def _source_name_summary(self, source_file_names: list[str]) -> str:
        cleaned = [item.strip() for item in source_file_names if item and item.strip()]
        if not cleaned:
            return "未命名素材"
        if len(cleaned) == 1:
            return cleaned[0]
        if len(cleaned) == 2:
            return "、".join(cleaned)
        return f"{cleaned[0]}、{cleaned[1]} 等 {len(cleaned)} 个素材"

    def get_task_trace(self, task_id: str, limit: int = 500) -> list[TaskTraceEvent]:
        logs = self.list_task_logs(task_id, limit=limit)
        if logs:
            return logs
        return read_task_trace(self.storage.task_trace_path(task_id), limit=limit)

    def list_task_logs(self, task_id: str, limit: int = 500) -> list[TaskTraceEvent]:
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError("task not found")
            rows = session.scalars(
                select(SystemLog)
                .where(SystemLog.task_id == task_id)
                .order_by(SystemLog.created_at.desc())
                .limit(limit)
            ).all()
        events: list[TaskTraceEvent] = []
        for row in reversed(rows):
            events.append(
                TaskTraceEvent(
                    timestamp=_iso(row.logged_at or row.created_at),
                    level=self._coerce_trace_level(str(row.level or "INFO")),
                    stage=_task_stage(row.stage),
                    event=row.event or "",
                    message=row.message or "",
                    payload=row.payload_json if isinstance(row.payload_json, dict) else {},
                )
            )
        return events

    def list_task_status_history(self, task_id: str, limit: int = 500) -> list[TaskStatusHistoryRecord]:
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError("task not found")
            rows = session.scalars(
                select(TaskStatusHistory)
                .where(TaskStatusHistory.task_id == task_id)
                .order_by(TaskStatusHistory.created_at.desc())
                .limit(limit)
            ).all()
        records: list[TaskStatusHistoryRecord] = []
        for row in reversed(rows):
            previous = str(row.previous_status or "").strip() or None
            next_status = str(row.current_status or "PENDING").strip().upper()
            try:
                next_enum = TaskStatus(next_status)
            except Exception:
                next_enum = TaskStatus.PENDING
            previous_enum = None
            if previous:
                try:
                    previous_enum = TaskStatus(previous.upper())
                except Exception:
                    previous_enum = None
            records.append(
                TaskStatusHistoryRecord(
                    statusHistoryId=row.id,
                    taskId=row.task_id,
                    previousStatus=previous_enum,
                    nextStatus=next_enum,
                    progress=int(row.progress or 0),
                    stage=_task_stage(row.stage),
                    event=row.event or "",
                    reason=row.message or None,
                    operator=str(row.operator_type or "system"),
                    changedAt=_iso(row.changed_at or row.created_at),
                    payload=row.payload_json if isinstance(row.payload_json, dict) else {},
                )
            )
        return records

    def list_task_model_calls(self, task_id: str, limit: int = 500) -> list[TaskModelCallRecord]:
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError("task not found")
            rows = session.scalars(
                select(TaskModelCall)
                .where(TaskModelCall.task_id == task_id)
                .order_by(TaskModelCall.started_at.desc())
                .limit(limit)
            ).all()
        mapped: list[TaskModelCallRecord] = []
        for row in reversed(rows):
            status = TaskModelCallStatus.SUCCESS if row.success else TaskModelCallStatus.FAILED
            mapped.append(
                TaskModelCallRecord(
                    modelCallId=row.id,
                    taskId=row.task_id,
                    provider=row.provider or "unknown",
                    modelName=row.model_name or row.model_alias or "unknown",
                    operationKind=_task_operation(row.operation, stage=row.stage),
                    status=status,
                    latencyMs=int(row.duration_ms or 0),
                    requestPayload=row.request_payload_json if isinstance(row.request_payload_json, dict) else {},
                    responsePayload=row.response_payload_json if isinstance(row.response_payload_json, dict) else {},
                    responseCode=int(row.response_status_code or 0) or None,
                    errorCode=row.error_code or None,
                    errorMessage=row.error_message or None,
                    startedAt=_optional_iso(row.started_at),
                    finishedAt=_optional_iso(row.finished_at),
                    createdAt=_iso(row.created_at),
                )
            )
        return mapped

    def list_task_results(self, task_id: str) -> list[TaskOutputSchema]:
        detail = self.get_task_detail(task_id)
        return detail.outputs

    def list_task_materials(self, task_id: str) -> list[TaskMaterial]:
        detail = self.get_task_detail(task_id)
        return detail.materials

    def _status_from_trace_event(self, event: TaskTraceEvent) -> str | None:
        mapping = {
            "task.created": "PENDING",
            "task.retry_requested": "PENDING",
            "task.continue_requested": "PENDING",
            "task.claimed": "ANALYZING",
            "analysis.started": "ANALYZING",
            "planning.started": "PLANNING",
            "render.started": "RENDERING",
            "task.paused": "PAUSED",
            "task.paused_by_developer_setting": "PAUSED",
            "task.terminated": "FAILED",
            "task.completed": "COMPLETED",
            "task.failed": "FAILED",
        }
        return mapping.get(event.event)

    def query_seeddance_task_result(self, remote_task_id: str) -> SeeddanceTaskQueryResponse:
        normalized_task_id = str(remote_task_id or "").strip()
        if not normalized_task_id:
            raise ValueError("remote task id is required")

        provider = self.settings.model.providers.get("volcengine_seed")
        task_endpoint = str((provider.extras.get("task_base_url") if provider else "") or "").strip()
        api_key = str((provider.api_key if provider else "") or "").strip()
        if not task_endpoint:
            raise ValueError("seeddance video task endpoint is empty")
        if not api_key:
            raise ValueError("seeddance api key is empty")

        query_url = f"{task_endpoint.rstrip('/')}/{urllib.parse.quote(normalized_task_id)}"
        request = urllib.request.Request(
            query_url,
            method="GET",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
                "X-Api-Key": api_key,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.settings.model.timeout_seconds) as response:
                raw_response = response.read()
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="ignore")
            except Exception:
                detail = ""
            detail_text = truncate_text(detail.strip(), 320)
            if detail_text:
                raise RuntimeError(f"seeddance task query http error: {exc.code} {detail_text}") from exc
            raise RuntimeError(f"seeddance task query http error: {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"seeddance task query network error: {exc}") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise RuntimeError(f"seeddance task query timeout: {exc}") from exc

        try:
            payload = json.loads(raw_response.decode("utf-8"))
        except Exception as exc:
            raise RuntimeError("seeddance task query returned non-json response") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("seeddance task query returned non-object payload")

        parsed = self.generation_orchestrator.parse_remote_video_task_payload(payload)
        status = str(parsed.get("status") or "UNKNOWN").upper()
        message = parsed.get("message")
        video_url = parsed.get("videoUrl")
        resolved_task_id = str(parsed.get("taskId") or normalized_task_id)

        return SeeddanceTaskQueryResponse(
            taskId=resolved_task_id,
            status=status,
            videoUrl=video_url,
            message=message,
            payload=payload,
        )

    def create_generation_task(self, payload: CreateGenerationTaskRequest) -> TaskDetail:
        if payload.taskType != TaskType.GENERATION:
            raise ValueError("only generation task type is supported")

        prompt = self._resolve_task_creative_prompt(payload.creativePrompt)
        output_count = 1

        duration_mode = "auto" if payload.videoDurationSeconds == "auto" else "fixed"
        requested_duration = payload.videoDurationSeconds if isinstance(payload.videoDurationSeconds, int) else None
        model_min_duration, model_max_duration, _ = self._resolve_video_model_duration_constraints(
            payload.videoModel or self.settings.model.defaults.video_generation
        )
        if requested_duration is not None:
            resolved_duration = max(1, min(120, int(requested_duration)))
            min_duration = int(payload.minDurationSeconds or resolved_duration)
            max_duration = int(payload.maxDurationSeconds or resolved_duration)
        else:
            min_duration = int(payload.minDurationSeconds or model_min_duration)
            max_duration = int(payload.maxDurationSeconds or model_max_duration)
            resolved_duration = max(1, min(120, int(round((min_duration + max_duration) / 2))))
        min_duration = max(1, min(120, min_duration))
        max_duration = max(1, min(120, max_duration))
        if min_duration > max_duration:
            raise ValueError("minDurationSeconds must be less than or equal to maxDurationSeconds")

        task_id = new_id("task")
        with self.session() as session:
            task = Task(
                id=task_id,
                task_type=TaskType.GENERATION.value,
                title=payload.title,
                source_material_id="",
                source_file_name="text_prompt",
                source_material_ids_json=[],
                source_file_names_json=[],
                platform=payload.platform,
                aspect_ratio=payload.aspectRatio,
                min_duration_seconds=min_duration,
                max_duration_seconds=max_duration,
                output_count=output_count,
                intro_template="none",
                outro_template="none",
                creative_prompt=prompt,
                execution_mode="generation",
                status="PENDING",
                progress=0,
            )
            session.add(task)
            session.commit()
        self._save_task_context(
            task_id,
            transcript_text=payload.transcriptText,
        )
        context_payload = self._load_task_context(task_id)
        context_payload.update(
            {
                "mode": TaskType.GENERATION.value,
                "textAnalysisModel": payload.textAnalysisModel or "",
                "videoModel": payload.videoModel or "",
                "videoSize": payload.videoSize or "",
                "durationMode": duration_mode,
                "durationSeconds": resolved_duration,
                "requestedDurationSeconds": payload.videoDurationSeconds if payload.videoDurationSeconds is not None else "",
                "stopBeforeVideoGeneration": bool(payload.stopBeforeVideoGeneration),
            }
        )
        self.storage.save_task_context(task_id, context_payload)
        self._trace(
            task_id,
            TaskStage.API.value,
            "task.created",
            "生成任务已创建。",
            {
                "task_type": TaskType.GENERATION.value,
                "output_count": output_count,
                "video_model": payload.videoModel or "",
                "text_analysis_model": payload.textAnalysisModel or "",
                "video_size": payload.videoSize or "",
                "duration_mode": duration_mode,
                "duration_seconds": resolved_duration,
                "min_duration_seconds": min_duration,
                "max_duration_seconds": max_duration,
                "stop_before_video_generation": bool(payload.stopBeforeVideoGeneration),
                "creative_prompt_source": "custom"
                if str(payload.creativePrompt or "").strip()
                else "system_default",
            },
        )
        self.dispatch_task(task_id)
        return self.get_task_detail(task_id)

    def list_tasks(
        self,
        q: str | None = None,
        status: str | None = None,
        platform: str | None = None,
    ) -> list[TaskListItem]:
        with self.session() as session:
            stmt = select(Task).options(selectinload(Task.results))
            filters = []
            if q:
                pattern = f"%{q}%"
                filters.append(
                    (
                        Task.title.ilike(pattern)
                        | Task.source_file_name.ilike(pattern)
                        | Task.creative_prompt.ilike(pattern)
                    )
                )
            if status:
                filters.append(Task.status == status)
            if platform:
                filters.append(Task.platform == platform)
            if filters:
                stmt = stmt.where(*filters)
            rows = session.scalars(stmt.order_by(Task.created_at.desc())).all()
            return [self._task_to_list_item(row) for row in rows]

    def get_admin_overview(self) -> AdminOverview:
        tasks = self.list_tasks()
        total = len(tasks)
        text_model = self.model_router.resolve(capability="text_analysis", kind="text")
        return AdminOverview(
            generatedAt=_iso(utcnow()),
            counts=AdminOverviewCounts(
                totalTasks=total,
                queuedTasks=len([task for task in tasks if task.status in {"PENDING", "PAUSED"}]),
                runningTasks=len([task for task in tasks if task.status in {"ANALYZING", "PLANNING", "RENDERING"}]),
                completedTasks=len([task for task in tasks if task.status == "COMPLETED"]),
                failedTasks=len([task for task in tasks if task.status == "FAILED"]),
                semanticTasks=len([task for task in tasks if task.hasTranscript]),
                timedSemanticTasks=len([task for task in tasks if task.hasTimedTranscript]),
                averageProgress=round(sum(task.progress for task in tasks) / total) if total else 0,
            ),
            modelReady=bool(
                text_model.provider_name
                and text_model.model_name
                and text_model.base_url
                and text_model.api_key
            ),
            primaryModel=text_model.model_name,
            textModel=text_model.model_name,
            visionModel=self.settings.model.defaults.vision_analysis,
            recentTasks=tasks[:8],
            recentFailures=[task for task in tasks if task.status == "FAILED"][:6],
            recentRunningTasks=[task for task in tasks if task.status in {"ANALYZING", "PLANNING", "RENDERING"}][:6],
            recentTraceCount=len(self.list_admin_traces(limit=120)),
        )

    def list_admin_traces(
        self,
        *,
        limit: int = 200,
        task_id: str | None = None,
        stage: str | None = None,
        level: str | None = None,
        q: str | None = None,
    ) -> list[AdminTraceEvent]:
        trace_dir = self.storage.temp_root / "task_trace"
        if not trace_dir.exists():
            return []

        requested_task_id = (task_id or "").strip()
        normalized_stage = (stage or "").strip()
        normalized_level = (level or "").strip().upper()
        keyword = (q or "").strip().lower()

        tasks_by_id: dict[str, TaskListItem] = {task.id: task for task in self.list_tasks()}
        candidate_paths: list[Path]
        if requested_task_id:
            candidate_paths = [self.storage.task_trace_path(requested_task_id)]
        else:
            candidate_paths = sorted(trace_dir.glob("*.jsonl"), reverse=True)

        combined: list[AdminTraceEvent] = []
        per_file_limit = max(50, limit)
        for path in candidate_paths:
            if not path.exists():
                continue
            current_task_id = path.stem
            task_meta = tasks_by_id.get(current_task_id)
            events = read_task_trace(path, limit=per_file_limit)
            for event in events:
                if normalized_stage and event.stage != normalized_stage:
                    continue
                if normalized_level and event.level.upper() != normalized_level:
                    continue
                if keyword:
                    haystack = " ".join(
                        [
                            current_task_id,
                            event.stage,
                            event.event,
                            event.message,
                            json.dumps(event.payload, ensure_ascii=False),
                            task_meta.title if task_meta else "",
                        ]
                    ).lower()
                    if keyword not in haystack:
                        continue
                combined.append(
                    AdminTraceEvent(
                        taskId=current_task_id,
                        taskTitle=task_meta.title if task_meta else None,
                        taskStatus=task_meta.status.value if task_meta else None,
                        **event.model_dump(),
                    )
                )

        combined.sort(key=lambda item: item.timestamp, reverse=True)
        return combined[:limit]

    def get_task_detail(self, task_id: str) -> TaskDetail:
        with self.session() as session:
            stmt = (
                select(Task)
                .options(selectinload(Task.results))
                .where(Task.id == task_id)
            )
            task = session.scalars(stmt).one_or_none()
            if task is None:
                raise LookupError("task not found")
            return self._task_to_detail(task)

    def retry_task(self, task_id: str) -> TaskDetail:
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError("task not found")
            self._delete_outputs(session, task)
            task.status = "PENDING"
            task.progress = 0
            task.error_message = ""
            task.plan_json = ""
            task.started_at = None
            task.finished_at = None
            task.retry_count = (task.retry_count or 0) + 1
            session.commit()
        context_payload = self._load_task_context(task_id)
        context_payload.pop("pauseRequested", None)
        context_payload.pop("pauseReason", None)
        context_payload.pop("resumeReuseAnalysis", None)
        context_payload.pop("pausedByDeveloperMode", None)
        context_payload.pop("terminateRequested", None)
        context_payload.pop("terminateReason", None)
        context_payload.pop("terminateMessage", None)
        context_payload.pop("keyframeStatus", None)
        context_payload.pop("keyframeRunId", None)
        context_payload.pop("keyframeOutputUrl", None)
        context_payload.pop("keyframeRemoteSourceUrl", None)
        context_payload.pop("keyframeModel", None)
        context_payload.pop("keyframeProvider", None)
        context_payload.pop("keyframeError", None)
        self.storage.save_task_context(task_id, context_payload)

        self._trace(
            task_id,
            "api",
            "task.retry_requested",
            "Task retry requested.",
            {
                "retry_count": self.get_task_detail(task_id).retryCount,
            },
        )
        self.dispatch_task(task_id)
        return self.get_task_detail(task_id)

    def pause_task(self, task_id: str) -> TaskDetail:
        previous_status = ""
        immediate_paused = False
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError("task not found")
            if task.status in {"COMPLETED", "FAILED"}:
                raise ValueError("已结束任务不支持暂停。")
            if task.status == "RENDERING":
                raise ValueError("渲染中的任务暂不支持暂停，请等待当前生成片段完成后再操作。")
            if task.status == "PAUSED":
                return self._task_to_detail(task)
            previous_status = str(task.status or "")
            if task.status == "PENDING":
                task.status = "PAUSED"
                task.progress = max(1, int(task.progress or 0))
                immediate_paused = True
            session.commit()

        context_payload = self._load_task_context(task_id)
        context_payload["pauseRequested"] = True
        context_payload["pauseReason"] = "manual"
        self.storage.save_task_context(task_id, context_payload)

        if immediate_paused:
            self._trace(
                task_id,
                "api",
                "task.paused",
                "任务已暂停。",
                {
                    "reason": "manual",
                    "previous_status": previous_status,
                    "immediate": True,
                },
            )
        else:
            self._trace(
                task_id,
                "api",
                "task.pause_requested",
                "已收到暂停请求，将在当前阶段结束后暂停。",
                {
                    "reason": "manual",
                    "status": previous_status,
                    "immediate": False,
                },
                "WARN",
            )
        return self.get_task_detail(task_id)

    def continue_task(self, task_id: str) -> TaskDetail:
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError("task not found")
            if task.status != "PAUSED":
                raise ValueError("仅支持继续已暂停任务。")
            task.status = "PENDING"
            task.progress = max(1, int(task.progress or 0))
            task.error_message = ""
            task.finished_at = None
            session.commit()

        context_payload = self._load_task_context(task_id)
        paused_by_developer_mode = self._context_paused_by_developer_mode(context_payload)
        context_payload["pauseRequested"] = False
        context_payload.pop("pauseReason", None)
        context_payload.pop("terminateRequested", None)
        context_payload.pop("terminateReason", None)
        context_payload.pop("terminateMessage", None)
        if paused_by_developer_mode:
            context_payload["stopBeforeVideoGeneration"] = False
            context_payload["resumeReuseAnalysis"] = True
            context_payload["pausedByDeveloperMode"] = False
        else:
            context_payload.pop("resumeReuseAnalysis", None)
        self.storage.save_task_context(task_id, context_payload)

        self._trace(
            task_id,
            "api",
            "task.continue_requested",
            "任务已继续执行。",
            {
                "paused_by_developer_mode": paused_by_developer_mode,
            },
        )
        self.dispatch_task(task_id)
        return self.get_task_detail(task_id)

    def terminate_task(self, task_id: str) -> TaskDetail:
        termination_message = "任务已手动终止。"
        previous_status = ""
        changed = False
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError("task not found")
            if task.status == "COMPLETED":
                raise ValueError("已完成任务不支持终止。")
            previous_status = str(task.status or "")
            if task.status != "FAILED" or str(task.error_message or "").strip() != termination_message:
                task.status = "FAILED"
                task.progress = max(1, min(99, int(task.progress or 0)))
                task.error_message = termination_message
                task.finished_at = utcnow()
                session.commit()
                changed = True

        context_payload = self._load_task_context(task_id)
        context_payload["terminateRequested"] = True
        context_payload["terminateReason"] = "manual"
        context_payload["terminateMessage"] = termination_message
        context_payload["pauseRequested"] = False
        context_payload.pop("pauseReason", None)
        self.storage.save_task_context(task_id, context_payload)

        self._trace(
            task_id,
            "api",
            "task.terminated",
            "任务已终止。",
            {
                "reason": "manual",
                "previous_status": previous_status,
                "changed": changed,
            },
            "WARN",
        )
        return self.get_task_detail(task_id)

    def delete_task(self, task_id: str) -> TaskDeleteResult:
        with self.session() as session:
            task = session.scalar(
                select(Task)
                .options(selectinload(Task.results))
                .where(Task.id == task_id)
            )
            if task is None:
                raise LookupError("task not found")
            if task.status in {"ANALYZING", "PLANNING", "RENDERING"}:
                raise ValueError("进行中的任务不能直接删除，请等待任务完成或失败后再删除。")

            self._trace(
                task_id,
                "api",
                "task.delete_requested",
                "已收到删除任务请求。",
                {"status": task.status},
                "WARN",
            )
            self._delete_outputs(session, task)
            session.delete(task)
            session.commit()

        self.storage.remove_task_artifacts(task_id)
        return TaskDeleteResult(taskId=task_id, deleted=True)

    def bulk_delete_tasks(self, task_ids: list[str]) -> AdminTaskBatchResult:
        succeeded: list[str] = []
        failed: list[AdminTaskActionFailure] = []
        for task_id in task_ids:
            try:
                self.delete_task(task_id)
                succeeded.append(task_id)
            except Exception as exc:
                failed.append(AdminTaskActionFailure(taskId=task_id, reason=str(exc)))
        return AdminTaskBatchResult(
            action="delete",
            requestedCount=len(task_ids),
            succeededTaskIds=succeeded,
            failed=failed,
        )

    def bulk_retry_tasks(self, task_ids: list[str]) -> AdminTaskBatchResult:
        succeeded: list[str] = []
        failed: list[AdminTaskActionFailure] = []
        for task_id in task_ids:
            try:
                self.retry_task(task_id)
                succeeded.append(task_id)
            except Exception as exc:
                failed.append(AdminTaskActionFailure(taskId=task_id, reason=str(exc)))
        return AdminTaskBatchResult(
            action="retry",
            requestedCount=len(task_ids),
            succeededTaskIds=succeeded,
            failed=failed,
        )

    def list_pending_task_ids(self, limit: int = 10) -> list[str]:
        with self.session() as session:
            rows = session.scalars(
                select(Task.id)
                .where(Task.status == "PENDING")
                .order_by(Task.created_at.asc())
                .limit(limit)
            ).all()
            return list(rows)

    def _process_generation_task(self, task_id: str) -> None:
        try:
            with self.session() as session:
                task = session.get(Task, task_id)
                if task is None:
                    return
                task_title = str(task.title or "").strip() or task_id
                task_aspect_ratio = str(task.aspect_ratio or "9:16").strip() or "9:16"
                context_payload = self._load_task_context(task_id)
                prompt = self._resolve_task_creative_prompt(task.creative_prompt)
                transcript_text = self._context_transcript(context_payload)
                analysis_source_text = transcript_text or prompt
                if transcript_text and prompt and prompt not in transcript_text:
                    analysis_source_text = f"{transcript_text}\n\n【创作目标与风格要求】\n{prompt}"
                output_count = max(1, int(task.output_count or 1))
                text_model = str(context_payload.get("textAnalysisModel") or "").strip() or None
                video_model = str(context_payload.get("videoModel") or "").strip() or None
                video_size = str(context_payload.get("videoSize") or "").strip() or None
                duration_mode = str(context_payload.get("durationMode") or "").strip().lower()
                if duration_mode not in {"auto", "fixed"}:
                    requested_duration_mode = str(context_payload.get("requestedDurationSeconds") or "").strip().lower()
                    duration_mode = "auto" if requested_duration_mode == "auto" else "fixed"
                duration_raw = context_payload.get("durationSeconds")
                fallback_duration = int(
                    task.max_duration_seconds
                    or task.min_duration_seconds
                    or self._default_generation_duration_seconds()
                )
                try:
                    duration_seconds = int(float(duration_raw)) if duration_raw not in {None, ""} else fallback_duration
                except Exception:
                    duration_seconds = fallback_duration
                if duration_seconds <= 0:
                    duration_seconds = fallback_duration
                duration_seconds = max(1, min(120, duration_seconds))
                min_duration = int(task.min_duration_seconds or duration_seconds or 5)
                max_duration = int(task.max_duration_seconds or duration_seconds or min_duration)
                if min_duration > max_duration:
                    min_duration, max_duration = max_duration, min_duration
                stop_before_video_generation = self._context_stop_before_video_generation(context_payload)
                self._raise_if_interrupt_requested(task_id, checkpoint="analysis.bootstrap")
                task.status = "ANALYZING"
                task.progress = max(10, int(task.progress or 0))
                task.started_at = task.started_at or utcnow()
                session.commit()

            analysis_target = self.model_router.resolve(text_model, capability="text_analysis", kind="text")
            self._trace(
                task_id,
                "analysis",
                "analysis.started",
                "生成任务进入文本分析阶段。",
                {
                    "task_type": TaskType.GENERATION.value,
                    "model": text_model or analysis_target.model_name,
                    "provider": analysis_target.provider_name,
                    "output_count": output_count,
                    "analysis_text_source": "transcript" if transcript_text else "creative_prompt",
                    "analysis_text_length": len(analysis_source_text),
                },
            )

            analysis_prompt = prompt
            analysis_script_text = ""
            analysis_run_id = ""
            analysis_model_info: dict[str, object] = {}
            analysis_call_chain: list[dict[str, object]] = []
            analysis_failure_message = ""
            reuse_analysis_result = self._context_resume_reuse_analysis(context_payload)
            if reuse_analysis_result:
                analysis_prompt = str(context_payload.get("analysisPrompt") or "").strip() or prompt
                analysis_script_text = str(context_payload.get("analysisScriptText") or "").strip()
                analysis_run_id = str(context_payload.get("analysisRunId") or "").strip()
                raw_model_info = context_payload.get("analysisModelInfo")
                raw_call_chain = context_payload.get("analysisCallChain")
                if isinstance(raw_model_info, dict):
                    analysis_model_info = dict(raw_model_info)
                if isinstance(raw_call_chain, list):
                    analysis_call_chain = [item for item in raw_call_chain if isinstance(item, dict)]
                context_payload["resumeReuseAnalysis"] = False
                self.storage.save_task_context(task_id, context_payload)
                self._trace(
                    task_id,
                    "analysis",
                    "analysis.reused",
                    "已复用暂停前的分析结果，继续执行生成。",
                    {
                        "analysis_run_id": analysis_run_id,
                        "has_script": bool(analysis_script_text),
                    },
                )
            else:
                try:
                    analysis_request = GenerationRunRequest(
                        kind="script",
                        input={"text": analysis_source_text},
                        model={"textAnalysisModel": text_model},
                        options={},
                    )
                    analysis_response = self.generation_orchestrator.create_run(analysis_request)
                    analysis_run_id = analysis_response.id
                    if analysis_response.status == GenerationRunStatus.SUCCEEDED and analysis_response.resultScript is not None:
                        analysis_result = analysis_response.resultScript
                        if isinstance(analysis_result.modelInfo, dict):
                            analysis_model_info = analysis_result.modelInfo
                        if isinstance(analysis_result.callChain, list):
                            analysis_call_chain = [item for item in analysis_result.callChain if isinstance(item, dict)]
                        analysis_markdown_path = str(getattr(analysis_result, "markdownPath", "") or "").strip()
                        analysis_markdown_url = str(getattr(analysis_result, "markdownUrl", "") or "").strip()
                        script_text = str(analysis_result.scriptMarkdown or analysis_result.sourceText or "").strip()
                        if script_text:
                            analysis_script_text = script_text
                            analysis_prompt = f"{prompt}\n\n{truncate_text(script_text, 1200)}"
                        context_payload["analysisRunId"] = analysis_run_id
                        if analysis_markdown_path:
                            context_payload["analysisScriptMarkdownPath"] = analysis_markdown_path
                        if analysis_markdown_url:
                            context_payload["analysisScriptMarkdownUrl"] = analysis_markdown_url
                        self.storage.save_task_context(task_id, context_payload)
                        self._trace(
                            task_id,
                            "analysis",
                            "analysis.completed",
                            "文本分析阶段完成。",
                            {
                                "run_id": analysis_run_id,
                                "model": text_model or analysis_target.model_name,
                                "provider": str(analysis_model_info.get("provider") or analysis_target.provider_name or ""),
                                "has_script": bool(script_text),
                                "markdown_path": analysis_markdown_path,
                            },
                        )
                    else:
                        error_message = analysis_response.error.message if analysis_response.error else "analysis run failed"
                        analysis_failure_message = str(error_message)
                        self._trace(
                            task_id,
                            "analysis",
                            "analysis.model_failed",
                            "文本分析模型不可用，已回退原始提示词。",
                            {
                                "run_id": analysis_run_id,
                                "model": text_model or analysis_target.model_name,
                                "provider": analysis_target.provider_name,
                                "error": error_message,
                            },
                            "WARN",
                        )
                except Exception as exc:
                    analysis_failure_message = str(exc)
                    self._trace(
                        task_id,
                        "analysis",
                        "analysis.model_failed",
                        "文本分析模型调用失败，已回退原始提示词。",
                        {
                            "model": text_model or analysis_target.model_name,
                            "provider": analysis_target.provider_name,
                            "error": str(exc),
                        },
                        "WARN",
                    )
            context_payload["analysisPrompt"] = analysis_prompt
            context_payload["analysisScriptText"] = analysis_script_text
            if analysis_run_id:
                context_payload["analysisRunId"] = analysis_run_id
            if analysis_model_info:
                context_payload["analysisModelInfo"] = analysis_model_info
            else:
                context_payload.pop("analysisModelInfo", None)
            if analysis_call_chain:
                context_payload["analysisCallChain"] = analysis_call_chain
            else:
                context_payload.pop("analysisCallChain", None)
            self.storage.save_task_context(task_id, context_payload)
            if _is_content_policy_blocked_error(analysis_failure_message):
                raise RuntimeError(
                    f"文本分析被内容安全策略拦截，任务已终止：{truncate_text(analysis_failure_message, 360) or analysis_failure_message}"
                )
            self._raise_if_interrupt_requested(task_id, checkpoint="analysis.completed")

            with self.session() as session:
                task = session.get(Task, task_id)
                if task is None:
                    return
                task.status = "PLANNING"
                task.progress = max(35, int(task.progress or 0))
                session.commit()
            self._trace(
                task_id,
                "planning",
                "planning.started",
                "生成任务进入编排阶段。",
                {
                    "model": text_model or analysis_target.model_name,
                    "provider": analysis_target.provider_name,
                    "analysis_run_id": analysis_run_id,
                    "analysis_call_chain_count": len(analysis_call_chain),
                },
            )
            shot_duration_ranges = self._extract_storyboard_shot_duration_ranges(analysis_script_text)
            if duration_mode == "auto":
                matched_duration_count = 0
                duration_source = "fallback"
                if shot_duration_ranges:
                    min_duration = max(1, min(120, min(item[0] for item in shot_duration_ranges)))
                    max_duration = max(min_duration, min(120, max(item[1] for item in shot_duration_ranges)))
                    duration_seconds = max(1, min(120, int(round((min_duration + max_duration) / 2))))
                    matched_duration_count = len(shot_duration_ranges)
                    duration_source = "storyboard_ranges"
                else:
                    resolved_duration, matched_duration_count = self._resolve_auto_duration_seconds(
                        analysis_script_text,
                        fallback_seconds=max_duration,
                    )
                    duration_seconds = resolved_duration
                    min_duration = max(1, min(120, min(min_duration, duration_seconds)))
                    max_duration = max(min_duration, min(120, max(max_duration, duration_seconds)))
                    duration_source = "script_average"
                with self.session() as session:
                    task = session.get(Task, task_id)
                    if task is not None:
                        task.min_duration_seconds = min_duration
                        task.max_duration_seconds = max_duration
                        session.commit()
                context_payload["durationSeconds"] = duration_seconds
                context_payload["resolvedDurationSeconds"] = duration_seconds
                self.storage.save_task_context(task_id, context_payload)
                self._trace(
                    task_id,
                    "planning",
                    "planning.duration_auto_resolved",
                    "自动时长已根据分镜脚本确定。",
                    {
                        "duration_seconds": duration_seconds,
                        "min_duration_seconds": min_duration,
                        "max_duration_seconds": max_duration,
                        "matched_duration_count": matched_duration_count,
                        "duration_source": duration_source,
                        "fallback_used": matched_duration_count == 0,
                    },
                )
            clip_prompts = self._build_sequential_clip_prompts(
                base_prompt=analysis_prompt,
                analysis_script_text=analysis_script_text,
                fallback_count=output_count,
            )
            output_count = max(1, len(clip_prompts))
            context_payload["resolvedOutputCount"] = output_count
            self.storage.save_task_context(task_id, context_payload)
            with self.session() as session:
                task = session.get(Task, task_id)
                if task is not None:
                    task.output_count = output_count
                    session.commit()
            self._trace(
                task_id,
                "planning",
                "planning.shots_resolved",
                "已完成分镜数量解析，按镜头顺序生成。",
                {
                    "output_count": output_count,
                    "from_storyboard": bool(analysis_script_text.strip()),
                },
            )
            self._raise_if_interrupt_requested(task_id, checkpoint="planning.completed")
            if stop_before_video_generation:
                context_payload["keyframeStatus"] = "skipped"
                context_payload.pop("keyframeRunId", None)
                context_payload.pop("keyframeOutputUrl", None)
                context_payload.pop("keyframeRemoteSourceUrl", None)
                context_payload.pop("keyframeModel", None)
                context_payload.pop("keyframeProvider", None)
                context_payload.pop("keyframeError", None)
                context_payload["analysisPrompt"] = analysis_prompt
                context_payload["analysisScriptText"] = analysis_script_text
                context_payload["pauseRequested"] = False
                context_payload["pauseReason"] = "developer_mode"
                context_payload["pausedByDeveloperMode"] = True
                self.storage.save_task_context(task_id, context_payload)
                self._trace(
                    task_id,
                    "planning",
                    "planning.keyframe_skipped_by_developer_setting",
                    "已按开发者模式跳过关键帧文生图。",
                    {
                        "stop_before_video_generation": True,
                        "keyframe_generation_skipped": True,
                    },
                )
                self._trace(
                    task_id,
                    "planning",
                    "planning.completed",
                    "编排阶段完成，开发者模式要求在关键帧与视频生成前停止。",
                    {
                        "output_count": output_count,
                        "video_size": video_size or "",
                        "duration_seconds": duration_seconds,
                        "stop_before_video_generation": True,
                        "keyframe_generation_skipped": True,
                    },
                )
                self._trace(
                    task_id,
                    "render",
                    "render.skipped_by_developer_setting",
                    "已按开发者模式跳过视频生成。",
                    {
                        "stop_before_video_generation": True,
                        "keyframe_generation_skipped": True,
                        "video_generation_skipped": True,
                    },
                )
                with self.session() as session:
                    task = session.get(Task, task_id)
                    if task is None:
                        return
                    task.status = "PAUSED"
                    task.progress = max(55, int(task.progress or 0))
                    task.finished_at = None
                    session.commit()
                self._trace(
                    task_id,
                    "pipeline",
                    "task.paused_by_developer_setting",
                    "开发者模式：任务已在视频生成前暂停，可在当前基础上继续生成。",
                    {
                        "outputs": 0,
                        "task_type": TaskType.GENERATION.value,
                        "stop_before_video_generation": True,
                        "keyframe_generation_skipped": True,
                        "video_generation_skipped": True,
                    },
                )
                return
            self._raise_if_interrupt_requested(task_id, checkpoint="planning.keyframe_generation")
            try:
                self._generate_planning_keyframe(
                    task_id=task_id,
                    task_title=task_title,
                    aspect_ratio=task_aspect_ratio,
                    prompt=prompt,
                    analysis_script_text=analysis_script_text,
                    text_model=text_model,
                    context_payload=context_payload,
                )
            except Exception as exc:
                image_model = str(self.settings.model.defaults.image_generation or "").strip()
                self._trace(
                    task_id,
                    "planning",
                    "planning.keyframe_failed",
                    "关键帧文生图异常，已降级继续后续流程。",
                    {
                        "model": image_model,
                        "provider": self._infer_image_provider(image_model),
                        "error": str(exc),
                    },
                    "WARN",
                )

            self._trace(
                task_id,
                "planning",
                "planning.completed",
                "编排阶段完成，进入视频生成。",
                {
                    "output_count": output_count,
                    "video_size": video_size or "",
                    "duration_seconds": duration_seconds,
                    "stop_before_video_generation": False,
                },
            )
            self._raise_if_interrupt_requested(task_id, checkpoint="planning.post_keyframe")

            with self.session() as session:
                task = session.get(Task, task_id)
                if task is None:
                    return
                task.status = "RENDERING"
                task.progress = max(55, int(task.progress or 0))
                session.commit()
            self._trace(
                task_id,
                "render",
                "render.started",
                "生成任务进入视频渲染阶段。",
                {
                    "model": video_model or "",
                    "provider": self.text_generator.infer_video_provider(video_model or ""),
                    "video_size": video_size or "",
                    "duration_seconds": duration_seconds,
                    "min_duration_seconds": min_duration,
                    "max_duration_seconds": max_duration,
                    "output_count": output_count,
                    "has_keyframe": bool(str(context_payload.get("keyframeOutputUrl") or "").strip()),
                },
            )

            model_min_duration, model_max_duration, model_fixed_duration = self._resolve_video_model_duration_constraints(video_model)
            effective_min_duration = max(1, min(120, int(min_duration)))
            effective_max_duration = max(effective_min_duration, min(120, int(max_duration)))
            if model_fixed_duration:
                effective_min_duration = model_min_duration
                effective_max_duration = model_max_duration
            else:
                effective_min_duration = max(effective_min_duration, model_min_duration)
                effective_max_duration = min(effective_max_duration, model_max_duration)
                if effective_min_duration > effective_max_duration:
                    effective_min_duration = model_min_duration
                    effective_max_duration = model_max_duration

            if (
                effective_min_duration != min_duration
                or effective_max_duration != max_duration
                or model_fixed_duration
            ):
                self._trace(
                    task_id,
                    "render",
                    "render.duration_constrained_by_model",
                    "已按视频模型能力约束镜头时长范围。",
                    {
                        "requested_min_duration_seconds": min_duration,
                        "requested_max_duration_seconds": max_duration,
                        "effective_min_duration_seconds": effective_min_duration,
                        "effective_max_duration_seconds": effective_max_duration,
                        "model_fixed_duration": model_fixed_duration,
                        "model_supported_min_duration_seconds": model_min_duration,
                        "model_supported_max_duration_seconds": model_max_duration,
                        "video_model": video_model or "",
                    },
                    "WARN",
                )

            clip_duration_plan = self._build_clip_duration_plan(
                clip_count=output_count,
                default_min_duration=effective_min_duration,
                default_max_duration=effective_max_duration,
                shot_duration_ranges=shot_duration_ranges,
            )

            keyframe_output_url = self._resolve_video_reference_image_url(
                context_payload=context_payload,
                video_model=video_model,
            )
            keyframe_run_id = str(context_payload.get("keyframeRunId") or "").strip()
            normalized_video_model = self.normalize_video_model_key(video_model or "")
            requires_reference_image = normalized_video_model == "seeddance-1.5-pro"
            if requires_reference_image and not keyframe_output_url:
                raise RuntimeError("seeddance-1.5-pro requires reference image url, but keyframe url is empty")

            for index, clip_prompt in enumerate(clip_prompts):
                self._raise_if_interrupt_requested(task_id, checkpoint=f"render.clip_{index + 1}_start")
                clip_duration_seconds, clip_min_duration, clip_max_duration = clip_duration_plan[index]

                clip_keyframe_output_url = keyframe_output_url
                clip_keyframe_run_id = keyframe_run_id
                if output_count > 1 and index > 0:
                    try:
                        self._generate_planning_keyframe(
                            task_id=task_id,
                            task_title=task_title,
                            aspect_ratio=task_aspect_ratio,
                            prompt=clip_prompt,
                            analysis_script_text="",
                            text_model=text_model,
                            context_payload=context_payload,
                        )
                        clip_keyframe_output_url = self._resolve_video_reference_image_url(
                            context_payload=context_payload,
                            video_model=video_model,
                        )
                        clip_keyframe_run_id = str(context_payload.get("keyframeRunId") or "").strip()
                        if clip_keyframe_output_url:
                            keyframe_output_url = clip_keyframe_output_url
                            keyframe_run_id = clip_keyframe_run_id
                        self._trace(
                            task_id,
                            "render",
                            "render.clip_keyframe_generated",
                            "已为当前镜头生成独立关键帧。",
                            {
                                "clip_index": index + 1,
                                "keyframe_output_url": clip_keyframe_output_url,
                                "keyframe_run_id": clip_keyframe_run_id,
                            },
                        )
                    except Exception as exc:
                        self._trace(
                            task_id,
                            "render",
                            "render.clip_keyframe_failed",
                            "当前镜头关键帧生成失败，回退使用上一张关键帧。",
                            {
                                "clip_index": index + 1,
                                "error": str(exc),
                                "fallback_keyframe_output_url": keyframe_output_url,
                            },
                            "WARN",
                        )

                if requires_reference_image and not clip_keyframe_output_url:
                    raise RuntimeError("seeddance-1.5-pro requires reference image url, but clip keyframe url is empty")
                video_input: dict[str, object] = {
                    "prompt": clip_prompt,
                    "videoSize": video_size,
                    "durationSeconds": clip_duration_seconds,
                    "minDurationSeconds": clip_min_duration,
                    "maxDurationSeconds": clip_max_duration,
                }
                if clip_keyframe_output_url:
                    extras: dict[str, object] = {
                        "referenceImageUrl": clip_keyframe_output_url,
                        "imageUrl": clip_keyframe_output_url,
                        "sourceImageUrl": clip_keyframe_output_url,
                    }
                    if clip_keyframe_run_id:
                        extras["keyframeRunId"] = clip_keyframe_run_id
                    video_input["extras"] = extras
                run_request = GenerationRunRequest(
                    kind="video",
                    input=video_input,
                    model={
                        "textAnalysisModel": text_model,
                        "videoModel": video_model,
                    },
                    options={},
                )
                call_started_at = utcnow()
                run_response = self.generation_orchestrator.create_run(run_request)
                call_finished_at = utcnow()
                if run_response.status != GenerationRunStatus.SUCCEEDED or run_response.resultVideo is None:
                    error_message = run_response.error.message if run_response.error else "generation run failed"
                    provider_guess = self.text_generator.infer_video_provider(video_model or "")
                    self._record_task_model_call(
                        task_id=task_id,
                        stage="render",
                        operation="generation.video",
                        provider=provider_guess,
                        provider_model=str(video_model or ""),
                        requested_model=str(video_model or ""),
                        resolved_model="",
                        request_payload=_json_safe_dict(run_request.model_dump()),
                        response_payload=_json_safe_dict(run_response.model_dump()),
                        success=False,
                        http_status=int(getattr(run_response.error, "httpStatus", 0) or 0) if run_response.error else 0,
                        error_code=str(run_response.error.code or "generation_failed") if run_response.error else "generation_failed",
                        error_message=error_message,
                    )
                    raise RuntimeError(error_message)

                result = run_response.resultVideo
                output_url = str(result.outputUrl or "").strip()
                if not output_url:
                    raise RuntimeError("generation result outputUrl is empty")
                model_info = result.modelInfo if isinstance(result.modelInfo, dict) else {}
                provider = str(model_info.get("provider") or "").strip() or self.text_generator.infer_video_provider(video_model or "")
                resolved_model = str(
                    model_info.get("resolvedModel")
                    or model_info.get("modelName")
                    or video_model
                    or ""
                ).strip()
                clip_duration = float(result.durationSeconds or clip_duration_seconds or clip_max_duration or 0.0)
                latency_ms = max(0, int((call_finished_at - call_started_at).total_seconds() * 1000))
                model_call_id = new_id("mdlcall")
                material_asset_id = new_id("asset")
                with self.session() as session:
                    task = session.get(Task, task_id)
                    if task is None:
                        raise LookupError("task not found")
                    session.add(
                        TaskModelCall(
                            id=model_call_id,
                            task_id=task_id,
                            call_kind="video_generation",
                            stage="render",
                            operation="generation.video",
                            provider=provider or "unknown",
                            provider_model=str(video_model or ""),
                            requested_model=str(video_model or ""),
                            resolved_model=resolved_model,
                            model_name=resolved_model or str(video_model or ""),
                            model_alias=str(model_info.get("providerModel") or video_model or ""),
                            endpoint_host=str(model_info.get("endpointHost") or ""),
                            request_id=str(model_info.get("requestId") or run_response.id or ""),
                            request_payload_json=_json_safe_dict(run_request.model_dump()),
                            response_payload_json=_json_safe_dict(run_response.model_dump()),
                            http_status=200,
                            response_status_code=200,
                            success=True,
                            latency_ms=latency_ms,
                            duration_ms=latency_ms,
                            input_tokens=int(model_info.get("inputTokens") or 0),
                            output_tokens=int(model_info.get("outputTokens") or 0),
                            started_at=call_started_at,
                            finished_at=call_finished_at,
                        )
                    )
                    session.add(
                        MaterialAsset(
                            id=material_asset_id,
                            task_id=task_id,
                            source_task_id="",
                            source_material_id="",
                            asset_role="output",
                            media_type="video",
                            title=f"{task.title} #{index + 1}",
                            origin_provider=provider,
                            origin_model=resolved_model,
                            remote_task_id=run_response.id,
                            remote_asset_id="",
                            original_file_name=f"{task_id}_{index + 1}.mp4",
                            stored_file_name="",
                            file_ext="mp4",
                            storage_provider="remote",
                            mime_type="video/mp4",
                            size_bytes=0,
                            sha256="",
                            duration_seconds=max(0.0, clip_duration),
                            width=max(0, int(result.width or 0)),
                            height=max(0, int(result.height or 0)),
                            has_audio=True,
                            local_path="",
                            local_file_path="",
                            public_url=output_url,
                            third_party_url=output_url,
                            remote_url=output_url,
                            metadata_json=_json_safe_dict({
                                "runId": run_response.id,
                                "callChain": result.callChain,
                                "modelInfo": model_info,
                            }),
                        )
                    )
                    session.add(
                        TaskResult(
                            id=new_id("result"),
                            task_id=task_id,
                            result_type="video",
                            clip_index=index + 1,
                            title=f"生成结果 #{index + 1}",
                            reason="文本生成短剧视频结果",
                            source_model_call_id=model_call_id,
                            material_asset_id=material_asset_id,
                            start_seconds=0.0,
                            end_seconds=max(0.0, clip_duration),
                            duration_seconds=max(0.0, clip_duration),
                            preview_path=output_url,
                            download_path=output_url,
                            width=max(0, int(result.width or 0)),
                            height=max(0, int(result.height or 0)),
                            mime_type="video/mp4",
                            size_bytes=0,
                            remote_url=output_url,
                            extra_json={
                                "runId": run_response.id,
                                "videoModel": video_model,
                                "textAnalysisModel": text_model,
                                "videoSize": video_size,
                            },
                        )
                    )
                    task.progress = min(95, 60 + int(35 * ((index + 1) / output_count)))
                    session.commit()
                self._trace(
                    task_id,
                    "render",
                    "render.clip_completed",
                    f"第 {index + 1} 条生成结果已完成。",
                    {
                        "clip_index": index + 1,
                        "run_id": run_response.id,
                        "model": resolved_model or video_model or "",
                        "provider": provider,
                        "output_url": output_url,
                    },
                )
                self._raise_if_interrupt_requested(task_id, checkpoint=f"render.clip_{index + 1}_completed")

            self._raise_if_interrupt_requested(task_id, checkpoint="render.completed")
            with self.session() as session:
                task = session.get(Task, task_id)
                if task is None:
                    return
                task.status = "COMPLETED"
                task.progress = 100
                task.finished_at = utcnow()
                session.commit()
            self._trace(
                task_id,
                "pipeline",
                "task.completed",
                "生成任务执行完成。",
                {"outputs": output_count, "task_type": TaskType.GENERATION.value},
            )
        except (TaskPausedError, TaskTerminatedError):
            return
        except Exception as exc:
            self._fail_task(task_id, exc, message="生成任务失败。")

    def dispatch_task(self, task_id: str) -> None:
        if self.settings.using_inline_execution or self.worker is None or self.worker.job_queue is None:
            self._trace(
                task_id,
                "dispatch",
                "task.dispatched_inline",
                "任务通过本地线程直接开始执行。",
                {"execution_mode": self.settings.app.execution_mode},
            )
            thread = threading.Thread(target=self.process_task, args=(task_id,), daemon=True)
            thread.start()
            return
        try:
            self.worker.job_queue.enqueue(task_id)
            self._trace(
                task_id,
                "dispatch",
                "task.enqueued",
                "任务已进入队列，等待 worker 处理。",
                {"queue_mode": True},
            )
        except Exception:
            self._trace(
                task_id,
                "dispatch",
                "task.enqueue_failed",
                "任务入队失败，已回退为本地线程执行。",
                {"queue_mode": True},
                "WARN",
            )
            thread = threading.Thread(target=self.process_task, args=(task_id,), daemon=True)
            thread.start()

    def process_task(self, task_id: str) -> None:
        if not self._claim_task(task_id):
            return
        self._trace(
            task_id,
            "pipeline",
            "task.processing_started",
            "任务进入处理流水线。",
            {},
        )
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                return
            normalized_task_type = _task_type(task.task_type)
        if normalized_task_type != TaskType.GENERATION.value:
            self._fail_task(
                task_id,
                RuntimeError(f"unsupported task type: {normalized_task_type or 'unknown'}"),
                message="任务类型已下线，仅支持文本生成任务。",
            )
            return
        self._process_generation_task(task_id)
        return

    def _record_task_model_call(
        self,
        *,
        task_id: str,
        stage: str,
        operation: str,
        provider: str,
        provider_model: str,
        requested_model: str,
        resolved_model: str,
        request_payload: dict[str, object],
        response_payload: dict[str, object],
        success: bool,
        http_status: int = 200,
        error_code: str = "",
        error_message: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> str:
        call_id = new_id("mdlcall")
        model_name = resolved_model or requested_model or provider_model or "unknown"
        started_at = utcnow()
        finished_at = utcnow()
        normalized_stage = _task_stage(stage)
        normalized_operation = _task_operation(operation, stage=normalized_stage)
        with self.session() as session:
            session.add(
                TaskModelCall(
                    id=call_id,
                    task_id=task_id,
                    call_kind=normalized_stage,
                    stage=normalized_stage,
                    operation=normalized_operation,
                    provider=provider or "unknown",
                    provider_model=provider_model,
                    requested_model=requested_model,
                    resolved_model=resolved_model,
                    model_name=model_name,
                    model_alias=provider_model or model_name,
                    endpoint_host="",
                    request_payload_json=request_payload,
                    response_payload_json=response_payload,
                    http_status=http_status,
                    response_status_code=http_status,
                    success=success,
                    error_code=error_code,
                    error_message=error_message,
                    latency_ms=0,
                    duration_ms=0,
                    input_tokens=max(0, int(input_tokens or 0)),
                    output_tokens=max(0, int(output_tokens or 0)),
                    started_at=started_at,
                    finished_at=finished_at,
                )
            )
            session.commit()
        return call_id

    def _claim_task(self, task_id: str) -> bool:
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None or task.status != "PENDING":
                return False
            context_payload = self._load_task_context(task_id)
            if self._context_terminate_requested(context_payload):
                task.status = "FAILED"
                task.progress = max(1, min(99, int(task.progress or 0)))
                task.error_message = truncate_text(
                    str(context_payload.get("terminateMessage") or "任务已手动终止。"),
                    1000,
                )
                task.finished_at = utcnow()
                session.commit()
                self._trace(
                    task_id,
                    "pipeline",
                    "task.terminated",
                    "任务在执行前已终止。",
                    {
                        "reason": str(context_payload.get("terminateReason") or "manual"),
                        "checkpoint": "claim",
                    },
                    "WARN",
                )
                return False
            if self._context_pause_requested(context_payload):
                task.status = "PAUSED"
                task.progress = max(1, int(task.progress or 0))
                session.commit()
                self._trace(
                    task_id,
                    "pipeline",
                    "task.paused",
                    "任务在执行前已暂停。",
                    {
                        "reason": str(context_payload.get("pauseReason") or "manual"),
                        "checkpoint": "claim",
                    },
                )
                return False
            task.status = "ANALYZING"
            task.progress = max(task.progress or 0, 1)
            task.started_at = task.started_at or utcnow()
            session.commit()
            self._trace(
                task_id,
                "pipeline",
                "task.claimed",
                "任务已被执行器接管，准备开始处理。",
                {
                    "status": task.status,
                },
            )
            return True

    def _delete_outputs(self, session: Session, task: Task) -> None:
        self.storage.remove_output_bundle(task.id)
        session.execute(
            delete(MaterialAsset)
            .where(MaterialAsset.task_id == task.id)
            .where(MaterialAsset.asset_role.in_(["output", "intermediate"]))
        )
        session.execute(delete(TaskResult).where(TaskResult.task_id == task.id))
        session.flush()

    def _task_to_list_item(self, task: Task) -> TaskListItem:
        context_payload = self._load_task_context(task.id)
        transcript_text = self._context_transcript(context_payload)
        source_material_ids, _ = self._resolve_task_source_selection(task, context_payload)
        return TaskListItem(
            id=task.id,
            title=task.title,
            status=task.status,
            platform=task.platform,
            progress=task.progress,
            createdAt=_iso(task.created_at),
            updatedAt=_iso(task.updated_at),
            sourceFileName=task.source_file_name,
            aspectRatio=task.aspect_ratio,
            minDurationSeconds=task.min_duration_seconds,
            maxDurationSeconds=task.max_duration_seconds,
            retryCount=task.retry_count or 0,
            startedAt=_optional_iso(task.started_at),
            finishedAt=_optional_iso(task.finished_at),
            completedOutputCount=len(task.results),
            hasTranscript=bool(transcript_text),
            hasTimedTranscript=bool(parse_transcript_cues(transcript_text)),
            sourceAssetCount=len(source_material_ids),
            editingMode=self._context_editing_mode(context_payload),
        )

    def _source_asset_summary(self, asset: MaterialAsset | None) -> SourceAssetSummary | None:
        if asset is None:
            return None
        return SourceAssetSummary(
            assetId=asset.id,
            originalFileName=asset.original_file_name,
            storedFileName=asset.stored_file_name,
            fileUrl=asset.public_url or self.storage.build_public_url(asset.local_path),
            mimeType=asset.mime_type,
            sizeBytes=asset.size_bytes,
            sha256=asset.sha256,
            durationSeconds=asset.duration_seconds,
            width=asset.width,
            height=asset.height,
            hasAudio=asset.has_audio,
            createdAt=_iso(asset.created_at),
            updatedAt=_iso(asset.updated_at),
        )

    def _load_source_asset_summaries(self, source_material_ids: list[str]) -> list[SourceAssetSummary]:
        if not source_material_ids:
            return []
        with self.session() as session:
            assets = [
                session.get(MaterialAsset, source_material_id)
                for source_material_id in list(dict.fromkeys(source_material_ids))
            ]
        return [summary for summary in (self._source_asset_summary(asset) for asset in assets) if summary is not None]

    def _task_sources_from_relation(self, task: Task) -> tuple[list[str], list[str]]:
        raw_ids = task.source_material_ids_json if isinstance(task.source_material_ids_json, list) else []
        raw_names = task.source_file_names_json if isinstance(task.source_file_names_json, list) else []
        source_material_ids = [str(item).strip() for item in raw_ids if str(item).strip()]
        source_file_names = [str(item).strip() for item in raw_names if str(item).strip()]
        return list(dict.fromkeys(source_material_ids)), source_file_names

    def _resolve_task_source_selection(
        self,
        task: Task,
        context_payload: dict[str, object],
    ) -> tuple[list[str], list[str]]:
        source_material_ids, source_file_names = self._task_sources_from_relation(task)
        if not source_material_ids:
            source_material_ids = self._context_source_material_ids(context_payload) or [task.source_material_id]
            source_file_names = self._context_source_file_names(context_payload) or [task.source_file_name]
        source_material_ids = [item.strip() for item in source_material_ids if isinstance(item, str) and item.strip()]
        source_file_names = [item.strip() for item in source_file_names if isinstance(item, str) and item.strip()]
        if not source_material_ids:
            return [], source_file_names[:1] if source_file_names else []
        if not source_file_names:
            source_file_names = [task.source_file_name]
        return [source_material_ids[0]], [source_file_names[0]]

    def _parse_plan(self, task: Task) -> list[ClipPlan]:
        if not task.plan_json:
            return []
        try:
            raw = json.loads(task.plan_json)
        except Exception:
            return []
        if not isinstance(raw, list):
            return []

        plan: list[ClipPlan] = []
        for item in raw:
            try:
                plan.append(ClipPlan.model_validate(item))
            except Exception:
                continue
        return plan

    def _load_task_context(self, task_id: str) -> dict[str, object]:
        return self.storage.load_task_context(task_id)

    def _context_source_material_ids(self, payload: dict[str, object]) -> list[str]:
        raw = payload.get("sourceAssetIds")
        if not isinstance(raw, list):
            return []
        values = [str(item).strip() for item in raw if str(item).strip()]
        return list(dict.fromkeys(values))

    def _context_source_file_names(self, payload: dict[str, object]) -> list[str]:
        raw = payload.get("sourceFileNames")
        if not isinstance(raw, list):
            return []
        return [str(item).strip() for item in raw if str(item).strip()]

    def _context_editing_mode(self, payload: dict[str, object]) -> str:
        return "drama"

    def _context_storyboard_script(self, payload: dict[str, object]) -> str | None:
        raw = payload.get("storyboardScript")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return None

    def _context_stop_before_video_generation(self, payload: dict[str, object]) -> bool:
        raw = payload.get("stopBeforeVideoGeneration")
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, (int, float)):
            return raw != 0
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "yes", "on"}
        return False

    def _resolve_video_reference_image_url(
        self,
        *,
        context_payload: dict[str, object],
        video_model: str | None,
    ) -> str:
        local_url = str(context_payload.get("keyframeOutputUrl") or "").strip()
        remote_url = str(context_payload.get("keyframeRemoteSourceUrl") or "").strip()
        normalized_video_model = self.normalize_video_model_key(video_model or "")
        if normalized_video_model == "seeddance-1.5-pro":
            if remote_url:
                return remote_url
            return local_url
        return local_url or remote_url

    def _context_pause_requested(self, payload: dict[str, object]) -> bool:
        raw = payload.get("pauseRequested")
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, (int, float)):
            return raw != 0
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "yes", "on"}
        return False

    def _context_terminate_requested(self, payload: dict[str, object]) -> bool:
        raw = payload.get("terminateRequested")
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, (int, float)):
            return raw != 0
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "yes", "on"}
        return False

    def _context_resume_reuse_analysis(self, payload: dict[str, object]) -> bool:
        raw = payload.get("resumeReuseAnalysis")
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, (int, float)):
            return raw != 0
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "yes", "on"}
        return False

    def _context_paused_by_developer_mode(self, payload: dict[str, object]) -> bool:
        raw = payload.get("pausedByDeveloperMode")
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, (int, float)):
            return raw != 0
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "yes", "on"}
        return False

    def _raise_if_terminate_requested(self, task_id: str, *, checkpoint: str) -> None:
        context_payload = self._load_task_context(task_id)
        if not self._context_terminate_requested(context_payload):
            return
        terminate_reason = str(context_payload.get("terminateReason") or "manual")
        terminate_message = truncate_text(str(context_payload.get("terminateMessage") or "任务已手动终止。"), 1000)
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise TaskTerminatedError("task terminated")
            if task.status != "FAILED":
                task.status = "FAILED"
                task.progress = max(1, min(99, int(task.progress or 0)))
                task.error_message = terminate_message
                task.finished_at = utcnow()
                session.commit()
        raise TaskTerminatedError(f"task terminated at {checkpoint} ({terminate_reason})")

    def _raise_if_pause_requested(self, task_id: str, *, checkpoint: str) -> None:
        context_payload = self._load_task_context(task_id)
        if not self._context_pause_requested(context_payload):
            return
        pause_reason = str(context_payload.get("pauseReason") or "manual")
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise TaskPausedError("task paused")
            if task.status != "PAUSED":
                task.status = "PAUSED"
                task.progress = max(1, min(99, int(task.progress or 0)))
                task.finished_at = None
                session.commit()
        self._trace(
            task_id,
            "pipeline",
            "task.paused",
            "任务已暂停。",
            {
                "reason": pause_reason,
                "checkpoint": checkpoint,
            },
        )
        raise TaskPausedError("task paused")

    def _raise_if_interrupt_requested(self, task_id: str, *, checkpoint: str) -> None:
        self._raise_if_terminate_requested(task_id, checkpoint=checkpoint)
        self._raise_if_pause_requested(task_id, checkpoint=checkpoint)

    def _coerce_trace_level(self, value: str) -> TraceLevel:
        normalized = str(value or "INFO").strip().upper()
        if normalized == "WARNING":
            normalized = "WARN"
        try:
            return TraceLevel(normalized)
        except Exception:
            return TraceLevel.INFO

    def _trace(
        self,
        task_id: str,
        stage: str,
        event: str,
        message: str,
        payload: dict[str, object] | None = None,
        level: str = "INFO",
    ) -> None:
        safe_payload = _json_safe_dict(payload)
        level_enum = self._coerce_trace_level(level)
        normalized_stage = _task_stage(stage)
        writer = TaskTraceWriter(task_id=task_id, trace_path=self.storage.task_trace_path(task_id))
        writer.log(stage=normalized_stage, event=event, message=message, payload=safe_payload, level=level_enum.value)

        status_candidate = self._status_from_trace_event(
            TaskTraceEvent(
                timestamp=_iso(utcnow()),
                level=level_enum,
                stage=normalized_stage,
                event=event,
                message=message,
                payload=safe_payload,
            )
        )
        with self.session() as session:
            session.add(
                SystemLog(
                    id=new_id("log"),
                    task_id=str(task_id or ""),
                    trace_id=str(safe_payload.get("traceId") or ""),
                    level=level_enum.value,
                    module="task.pipeline",
                    stage=normalized_stage,
                    event=event,
                    message=truncate_text(message, 1000) or "",
                    payload_json=safe_payload,
                    source="backend",
                    service_name="pipeline",
                    host_name=socket.gethostname(),
                    logged_at=utcnow(),
                )
            )

            if status_candidate:
                task = session.get(Task, task_id)
                previous_status = session.scalars(
                    select(TaskStatusHistory.current_status)
                    .where(TaskStatusHistory.task_id == task_id)
                    .order_by(TaskStatusHistory.created_at.desc())
                    .limit(1)
                ).first()
                current_status = str(previous_status or (task.status if task is not None else "") or "").strip()
                if current_status == status_candidate:
                    current_status = ""
                session.add(
                    TaskStatusHistory(
                        id=new_id("sthis"),
                        task_id=task_id,
                        previous_status=current_status,
                        current_status=status_candidate,
                        progress=int((safe_payload.get("progress") if isinstance(safe_payload.get("progress"), int) else (task.progress if task is not None else 0)) or 0),
                        stage=normalized_stage,
                        event=event,
                        message=truncate_text(message, 1000) or "",
                        operator_type="system",
                        operator_id="task-service",
                        payload_json=safe_payload,
                        changed_at=utcnow(),
                    )
                )

            model_name = str(
                safe_payload.get("model")
                or safe_payload.get("model_name")
                or safe_payload.get("primary_model")
                or safe_payload.get("requested_model")
                or ""
            ).strip()
            provider = str(safe_payload.get("provider") or safe_payload.get("model_provider") or "").strip()
            is_model_event = normalized_stage in {
                TaskStage.PLANNING.value,
                TaskStage.GENERATION.value,
                TaskStage.ANALYSIS.value,
                TaskStage.RENDER.value,
            } and bool(model_name or provider or "model" in event)
            if is_model_event:
                session.add(
                    TaskModelCall(
                        id=new_id("mdlcall"),
                        task_id=task_id,
                        stage=normalized_stage,
                        operation=_task_operation(event, stage=normalized_stage),
                        provider=provider or "unknown",
                        model_name=model_name or "unknown",
                        model_alias=str(safe_payload.get("resolved_model") or safe_payload.get("resolvedModel") or model_name or ""),
                        endpoint_host=str(safe_payload.get("endpoint_host") or ""),
                        request_id=str(safe_payload.get("request_id") or safe_payload.get("requestId") or ""),
                        request_payload_json=safe_payload,
                        response_payload_json={},
                        response_status_code=0,
                        duration_ms=0,
                        input_tokens=0,
                        output_tokens=0,
                        success=level_enum not in {TraceLevel.ERROR, TraceLevel.WARN},
                        error_code="",
                        error_message=message if level_enum in {TraceLevel.ERROR, TraceLevel.WARN} else "",
                        started_at=utcnow(),
                        finished_at=utcnow(),
                    )
                )
            session.commit()

    def _fail_task(self, task_id: str, exc: Exception, *, message: str = "任务处理失败。") -> None:
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is not None:
                task.status = "FAILED"
                task.progress = min(99, task.progress or 0)
                task.error_message = truncate_text(str(exc), 1000)
                task.finished_at = utcnow()
                session.commit()
        self._trace(
            task_id,
            "pipeline",
            "task.failed",
            message,
            {
                "error": str(exc),
            },
            "ERROR",
        )

    def _save_task_context(
        self,
        task_id: str,
        *,
        transcript_text: str | None = None,
        source_material_ids: list[str] | None = None,
        source_file_names: list[str] | None = None,
        storyboard_script: str | None = None,
    ) -> None:
        context = self._load_task_context(task_id)
        normalized_transcript = (transcript_text or "").strip()
        if normalized_transcript:
            context["transcriptText"] = normalized_transcript
        if source_material_ids:
            context["sourceAssetIds"] = list(dict.fromkeys([item for item in source_material_ids if item]))
        if source_file_names:
            context["sourceFileNames"] = [item for item in source_file_names if item]
        if storyboard_script is not None:
            normalized_storyboard = storyboard_script.strip()
            if normalized_storyboard:
                context["storyboardScript"] = normalized_storyboard
            else:
                context.pop("storyboardScript", None)
        self.storage.save_task_context(task_id, context)

    def _context_transcript(self, payload: dict[str, object]) -> str | None:
        raw = payload.get("transcriptText")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return None

    def _build_storyboard_script(
        self,
        task: Task,
        clips: list[ClipPlan],
        *,
        source_file_names: list[str],
        source_asset_count: int,
        editing_mode: str,
    ) -> str:
        mode_label = self._editing_mode_label(editing_mode)
        material_label = self._source_name_summary(source_file_names)
        lines = [
            "# 分镜脚本",
            "",
            f"- 任务标题：{task.title}",
            f"- 模式：{mode_label}",
            f"- 平台 / 画幅：{task.platform} / {task.aspect_ratio}",
            f"- 时长范围：{task.min_duration_seconds}-{task.max_duration_seconds} 秒",
            f"- 素材数量：{source_asset_count}",
            f"- 素材摘要：{material_label}",
        ]
        if task.creative_prompt:
            lines.extend(["", "## 创意提示词", "", task.creative_prompt.strip()])
        lines.extend(["", "## 分镜列表", ""])
        for clip in clips:
            lines.extend(
                [
                    f"### 分镜 {clip.clipIndex} · {clip.title}",
                    "",
                    f"- 时间窗：{_format_seconds_label(clip.startSeconds)} - {_format_seconds_label(clip.endSeconds)}",
                    f"- 时长：{_format_seconds_label(clip.durationSeconds)}",
                    f"- 设计意图：{clip.reason}",
                ]
            )
            if clip.segments:
                lines.extend(["", "| 素材 | 时间窗 | 时长 | 角色 |", "| --- | --- | --- | --- |"])
                for segment in clip.segments:
                    lines.append(
                        "| "
                        + " | ".join(
                            [
                                segment.sourceFileName or "-",
                                f"{_format_seconds_label(segment.startSeconds)} - {_format_seconds_label(segment.endSeconds)}",
                                _format_seconds_label(segment.durationSeconds),
                                segment.segmentRole or segment.segmentKind or "-",
                            ]
                        )
                        + " |"
                    )
            lines.append("")
        return "\n".join(lines).strip()

    def _build_task_materials(
        self,
        source_assets: list[SourceAssetSummary],
        outputs: list[TaskOutputSchema],
    ) -> list[TaskMaterial]:
        materials: list[TaskMaterial] = []
        for asset in source_assets:
            materials.append(
                TaskMaterial(
                    id=asset.assetId,
                    kind=MaterialKind.SOURCE,
                    mediaType=MediaType.VIDEO,
                    title=asset.originalFileName,
                    fileUrl=asset.fileUrl,
                    previewUrl=asset.fileUrl,
                    mimeType=asset.mimeType,
                    durationSeconds=asset.durationSeconds,
                    width=asset.width,
                    height=asset.height,
                    sizeBytes=asset.sizeBytes,
                    createdAt=asset.createdAt,
                )
            )
        for output in outputs:
            materials.append(
                TaskMaterial(
                    id=output.id,
                    kind=MaterialKind.OUTPUT,
                    mediaType=MediaType.VIDEO,
                    title=f"成片 #{output.clipIndex} · {output.title}",
                    fileUrl=output.downloadUrl,
                    previewUrl=output.previewUrl,
                    mimeType="video/mp4",
                    durationSeconds=output.durationSeconds,
                )
            )
        return materials

    def _transcript_preview(self, transcript_text: str | None, limit: int = 220) -> str | None:
        if not transcript_text:
            return None
        normalized = " ".join(line.strip() for line in transcript_text.splitlines() if line.strip())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3] + "..."

    def _task_to_detail(self, task: Task) -> TaskDetail:
        outputs: list[TaskOutputSchema] = []
        for output in sorted(task.results, key=lambda item: item.clip_index):
            preview_url = output.preview_path or output.remote_url
            download_url = output.download_path or output.remote_url
            outputs.append(
                TaskOutputSchema(
                    id=output.id,
                    clipIndex=output.clip_index,
                    title=output.title,
                    reason=output.reason,
                    startSeconds=output.start_seconds,
                    endSeconds=output.end_seconds,
                    durationSeconds=output.duration_seconds,
                    previewUrl=preview_url,
                    downloadUrl=download_url,
                )
            )
        source_asset: MaterialAsset | None = None
        with self.session() as session:
            source_asset = session.get(MaterialAsset, task.source_material_id)
        plan = self._parse_plan(task)
        context_payload = self._load_task_context(task.id)
        transcript_text = self._context_transcript(context_payload)
        transcript_cues = parse_transcript_cues(transcript_text)
        source_material_ids, source_file_names = self._resolve_task_source_selection(task, context_payload)
        source_assets = self._load_source_asset_summaries(source_material_ids)
        editing_mode = self._context_editing_mode(context_payload)
        storyboard_script = self._context_storyboard_script(context_payload)
        if not storyboard_script and plan:
            storyboard_script = self._build_storyboard_script(
                task,
                plan,
                source_file_names=source_file_names,
                source_asset_count=len(source_material_ids),
                editing_mode=editing_mode,
            )
        materials = self._build_task_materials(source_assets, outputs)
        return TaskDetail(
            id=task.id,
            title=task.title,
            status=task.status,
            platform=task.platform,
            progress=task.progress,
            createdAt=_iso(task.created_at),
            updatedAt=_iso(task.updated_at),
            sourceFileName=task.source_file_name,
            aspectRatio=task.aspect_ratio,
            minDurationSeconds=task.min_duration_seconds,
            maxDurationSeconds=task.max_duration_seconds,
            introTemplate=task.intro_template,
            outroTemplate=task.outro_template,
            creativePrompt=task.creative_prompt,
            errorMessage=task.error_message,
            startedAt=_optional_iso(task.started_at),
            finishedAt=_optional_iso(task.finished_at),
            retryCount=task.retry_count or 0,
            completedOutputCount=len(outputs),
            transcriptPreview=self._transcript_preview(transcript_text),
            hasTranscript=bool(transcript_text),
            hasTimedTranscript=bool(transcript_cues),
            transcriptCueCount=len(transcript_cues),
            source=self._source_asset_summary(source_asset),
            sourceAssets=source_assets or ([self._source_asset_summary(source_asset)] if source_asset is not None else []),
            storyboardScript=storyboard_script,
            materials=materials,
            sourceAssetIds=source_material_ids,
            sourceFileNames=source_file_names,
            sourceAssetCount=len(source_material_ids),
            editingMode=editing_mode,
            plan=plan,
            outputs=outputs,
        )
