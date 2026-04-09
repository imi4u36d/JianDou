from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from typing import Any, Callable

from ai_cut_ai.text_generation import (
    GenerateTextMediaRequest,
    GenerateTextMediaResponse,
    GenerateTextScriptRequest,
    GenerateTextScriptResponse,
    ProbeTextAnalysisModelRequest,
    ProbeTextAnalysisModelResponse,
    TextGenerationEngine,
)
from ai_cut_shared.schemas import (
    GenerationMediaKind,
    GenerationResultImage,
    GenerationResultProbe,
    GenerationResultScript,
    GenerationResultVideo,
    GenerationRunRequest,
    GenerationRunResponse,
    GenerationRunStatus,
    ModelCatalog,
    ModelConstraint,
    ProviderErrorEnvelope,
    VideoModelUsageResponse,
)
from ai_cut_shared.utils import new_id

from .adapters import AdapterRegistry


def _utcnow_iso() -> str:
    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"


class GenerationOrchestrator:
    def __init__(
        self,
        engine: TextGenerationEngine,
        *,
        registry: AdapterRegistry | None = None,
        usage_loader: Callable[[], VideoModelUsageResponse] | None = None,
        max_cached_runs: int = 500,
    ) -> None:
        self.engine = engine
        self.registry = registry or AdapterRegistry(engine)
        self.usage_loader = usage_loader
        self.max_cached_runs = max(20, max_cached_runs)
        self._runs: OrderedDict[str, GenerationRunResponse] = OrderedDict()

    def get_catalog(self) -> ModelCatalog:
        options = self.engine.list_options()
        constraints = [
            ModelConstraint.model_validate(item)
            for item in self.engine.get_model_constraints()
        ]
        return ModelCatalog(
            generatedAt=_utcnow_iso(),
            versions=list(getattr(options, "versions", []) or []),
            versionDetails=list(getattr(options, "versionDetails", []) or []),
            stylePresets=list(getattr(options, "stylePresets", []) or []),
            imageSizes=list(getattr(options, "imageSizes", []) or []),
            textAnalysisModels=list(getattr(options, "textAnalysisModels", []) or []),
            videoModels=list(getattr(options, "videoModels", []) or []),
            videoSizes=list(getattr(options, "videoSizes", []) or []),
            videoDurations=list(getattr(options, "videoDurations", []) or []),
            defaultVersion=getattr(options, "defaultVersion", None),
            defaultTextAnalysisModel=getattr(options, "defaultTextAnalysisModel", None),
            defaultVideoModel=getattr(options, "defaultVideoModel", None),
            defaultImageSize=getattr(options, "defaultImageSize", None),
            defaultVideoSize=getattr(options, "defaultVideoSize", None),
            defaultVideoDurationSeconds=getattr(options, "defaultVideoDurationSeconds", None),
            aliases=self.engine.get_model_aliases(),
            modelConstraints=constraints,
        )

    def create_run(self, payload: GenerationRunRequest) -> GenerationRunResponse:
        run_id = payload.id or new_id("run")
        created_at = _utcnow_iso()
        try:
            result = self._execute(payload, run_id)
            response = GenerationRunResponse(
                id=run_id,
                kind=payload.kind,
                status=GenerationRunStatus.SUCCEEDED,
                createdAt=created_at,
                updatedAt=_utcnow_iso(),
                result=result,
                resultImage=result if isinstance(result, GenerationResultImage) else None,
                resultVideo=result if isinstance(result, GenerationResultVideo) else None,
                resultScript=result if isinstance(result, GenerationResultScript) else None,
                resultProbe=result if isinstance(result, GenerationResultProbe) else None,
            )
        except Exception as exc:
            response = GenerationRunResponse(
                id=run_id,
                kind=payload.kind,
                status=GenerationRunStatus.FAILED,
                createdAt=created_at,
                updatedAt=_utcnow_iso(),
                error=ProviderErrorEnvelope(
                    code="generation_failed",
                    message=str(exc),
                    retriable=False,
                ),
            )
        self._remember_run(response)
        return response

    def get_run(self, run_id: str) -> GenerationRunResponse:
        response = self._runs.get(run_id)
        if response is None:
            raise LookupError("generation run not found")
        return response

    def list_usage(self) -> VideoModelUsageResponse:
        usage_adapter = self.registry.usage()
        if usage_adapter is not None:
            return usage_adapter.get_usage()
        if self.usage_loader is not None:
            return self.usage_loader()
        raw = self.engine.get_video_model_usage()
        return VideoModelUsageResponse.model_validate(raw)

    # Compatibility wrappers for existing TaskService/AgentPlatform call paths.
    def generate_text_image(self, payload: GenerateTextMediaRequest | dict[str, Any]) -> GenerateTextMediaResponse:
        return self.registry.image().generate(payload)

    def generate_text_video(self, payload: GenerateTextMediaRequest | dict[str, Any]) -> GenerateTextMediaResponse:
        return self.registry.video().generate(payload)

    def generate_text_script(self, payload: GenerateTextScriptRequest | dict[str, Any]) -> GenerateTextScriptResponse:
        return self.registry.text_analysis().generate_script(payload)

    def generate_text_script_with_source_file(
        self,
        payload: GenerateTextScriptRequest | dict[str, Any],
        *,
        source_text_file_path,
        source_text_file_name: str | None = None,
    ) -> GenerateTextScriptResponse:
        return self.engine.generate_text_script_with_source_file(
            payload,
            source_text_file_path=source_text_file_path,
            source_text_file_name=source_text_file_name,
        )

    def probe_text_analysis_model(
        self,
        payload: ProbeTextAnalysisModelRequest | dict[str, Any] | str | None = None,
    ) -> ProbeTextAnalysisModelResponse:
        return self.registry.text_analysis().probe(payload)

    def parse_remote_video_task_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "taskId": self.engine.extract_task_id(payload),
            "status": self.engine.extract_task_status(payload),
            "message": self.engine.extract_task_message(payload),
            "videoUrl": self.engine.extract_video_url(payload),
        }

    def normalize_video_model_key(self, model_name: str) -> str:
        return self.engine.normalize_video_model_key(model_name)

    def _remember_run(self, response: GenerationRunResponse) -> None:
        self._runs[response.id] = response
        self._runs.move_to_end(response.id)
        while len(self._runs) > self.max_cached_runs:
            self._runs.popitem(last=False)

    def _execute(
        self,
        payload: GenerationRunRequest,
        run_id: str,
    ) -> GenerationResultImage | GenerationResultVideo | GenerationResultScript | GenerationResultProbe:
        input_data = dict(payload.input or {})
        model_data = dict(payload.model or {})
        option_data = dict(payload.options or {})

        if payload.kind in {GenerationMediaKind.IMAGE, GenerationMediaKind.VIDEO}:
            return self._execute_media(
                payload=payload,
                run_id=run_id,
                input_data=input_data,
                model_data=model_data,
                option_data=option_data,
            )
        if payload.kind == "script":
            return self._execute_script(
                payload=payload,
                run_id=run_id,
                input_data=input_data,
                model_data=model_data,
                option_data=option_data,
            )
        if payload.kind == "probe":
            return self._execute_probe(
                payload=payload,
                run_id=run_id,
                model_data=model_data,
                input_data=input_data,
            )
        raise ValueError(f"unsupported kind: {payload.kind}")

    def _execute_media(
        self,
        *,
        payload: GenerationRunRequest,
        run_id: str,
        input_data: dict[str, Any],
        model_data: dict[str, Any],
        option_data: dict[str, Any],
    ) -> GenerationResultImage | GenerationResultVideo:
        prompt = str(input_data.get("prompt") or "").strip()
        if not prompt:
            raise ValueError("input.prompt is required")
        request_payload: dict[str, Any] = {
            "prompt": prompt,
            "kind": payload.kind,
            "version": input_data.get("version") or 1,
            "durationSeconds": input_data.get("durationSeconds"),
            "minDurationSeconds": input_data.get("minDurationSeconds"),
            "maxDurationSeconds": input_data.get("maxDurationSeconds"),
            "videoSize": input_data.get("videoSize"),
            "stylePreset": option_data.get("stylePreset") or input_data.get("stylePreset"),
            "textAnalysisModel": model_data.get("textAnalysisModel"),
            "providerModel": model_data.get("providerModel"),
            "videoModel": model_data.get("videoModel"),
            "extras": dict(input_data.get("extras") or {}),
        }
        if input_data.get("width") not in {None, ""}:
            request_payload["width"] = input_data.get("width")
        if input_data.get("height") not in {None, ""}:
            request_payload["height"] = input_data.get("height")
        if payload.kind == GenerationMediaKind.IMAGE:
            response = self.registry.image().generate(request_payload)
        else:
            response = self.registry.video().generate(request_payload)
        data = response.model_dump()
        media_kind = str(data.get("mediaType") or payload.kind)
        base_kwargs = {
            "runId": run_id,
            "kind": media_kind,
            "prompt": str(data.get("prompt") or prompt),
            "shapedPrompt": str(data.get("shapedPrompt") or ""),
            "metadata": data.get("metadata") if isinstance(data.get("metadata"), dict) else {},
            "modelInfo": data.get("modelInfo") if isinstance(data.get("modelInfo"), dict) else {},
            "callChain": data.get("callChain") if isinstance(data.get("callChain"), list) else [],
            "outputUrl": str(data.get("outputUrl") or data.get("fileUrl") or ""),
            "mimeType": str(data.get("mimeType") or "") or None,
            "width": int(data.get("width") or request_payload.get("width") or 0) or None,
            "height": int(data.get("height") or request_payload.get("height") or 0) or None,
        }
        if payload.kind == GenerationMediaKind.IMAGE:
            return GenerationResultImage.model_validate(base_kwargs)
        return GenerationResultVideo.model_validate(
            {
                **base_kwargs,
                "durationSeconds": (
                    float(data.get("durationSeconds"))
                    if data.get("durationSeconds") not in {None, ""}
                    else None
                ),
            }
        )

    def _execute_script(
        self,
        *,
        payload: GenerationRunRequest,
        run_id: str,
        input_data: dict[str, Any],
        model_data: dict[str, Any],
        option_data: dict[str, Any],
    ) -> GenerationResultScript:
        text = str(input_data.get("text") or input_data.get("prompt") or "").strip()
        if not text:
            raise ValueError("input.text is required for kind=script")
        response = self.registry.text_analysis().generate_script(
            {
                "text": text,
                "visualStyle": option_data.get("visualStyle") or input_data.get("visualStyle"),
                "textAnalysisModel": model_data.get("textAnalysisModel"),
            }
        )
        data = response.model_dump()
        return GenerationResultScript.model_validate(
            {
                "runId": run_id,
                "kind": "script",
                "prompt": text,
                "shapedPrompt": "",
                "metadata": data.get("metadata") if isinstance(data.get("metadata"), dict) else {},
                "modelInfo": data.get("modelInfo") if isinstance(data.get("modelInfo"), dict) else {},
                "callChain": data.get("callChain") if isinstance(data.get("callChain"), list) else [],
                "sourceText": str(data.get("sourceText") or text),
                "visualStyle": str(data.get("visualStyle") or option_data.get("visualStyle") or "AI 自动决策"),
                "outputFormat": data.get("outputFormat") or "markdown",
                "scriptMarkdown": str(data.get("scriptMarkdown") or ""),
                "markdownUrl": str(data.get("markdownFileUrl") or data.get("downloadUrl") or "") or None,
                "markdownPath": str(data.get("markdownFilePath") or "") or None,
            }
        )

    def _execute_probe(
        self,
        *,
        payload: GenerationRunRequest,
        run_id: str,
        model_data: dict[str, Any],
        input_data: dict[str, Any],
    ) -> GenerationResultProbe:
        requested_model = (
            model_data.get("textAnalysisModel")
            or input_data.get("textAnalysisModel")
            or None
        )
        response = self.registry.text_analysis().probe(
            {"textAnalysisModel": requested_model} if requested_model else {}
        )
        data = response.model_dump()
        return GenerationResultProbe.model_validate(
            {
                "runId": run_id,
                "kind": "probe",
                "prompt": str(requested_model or ""),
                "metadata": data,
                "modelInfo": {
                    "provider": data.get("provider"),
                    "requestedModel": data.get("requestedModel"),
                    "resolvedModel": data.get("resolvedModel"),
                    "endpointHost": data.get("endpointHost"),
                },
                "callChain": [],
                "ready": bool(data.get("ready", True)),
                "latencyMs": int(data.get("latencyMs") or 0),
            }
        )
