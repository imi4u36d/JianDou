"""Text probe facade with delegated script generation workflows."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from backend.domain.generation_run import GenerationModelKinds, GenerationRunKinds
from backend.services.generation_run_support import GenerationRunSupport
from backend.services.generation_script_run_service import GenerationScriptRunService
from backend.services.generation_text_run_values import text_provider_interaction, user_id_from_request

ProfileResolver = Callable[[str, int | None], dict[str, Any]]
TextModelCall = Callable[..., Awaitable[dict[str, Any]]]


class GenerationTextRunService:
    """Build text probes and retain the stable script-run entry points."""

    def __init__(
        self,
        support: GenerationRunSupport,
        prompt_resolver: Any,
        resolve_text_profile: ProfileResolver,
        call_text_model: TextModelCall,
    ) -> None:
        self._support = support
        self._resolve_text_profile = resolve_text_profile
        self._call_text_model = call_text_model
        self._script_runs = GenerationScriptRunService(
            support,
            prompt_resolver,
            resolve_text_profile,
            call_text_model,
        )

    async def create_probe_run(self, run_id: str, request: dict[str, Any]) -> dict[str, Any]:
        requested_model = self._support.required_model(
            self._support.nested_value(request, "model", "textAnalysisModel", ""),
            "textAnalysisModel",
            "",
        )
        profile = self._resolve_text_profile(requested_model, user_id_from_request(request))
        call_chain: list[dict[str, Any]] = []
        metadata: dict[str, Any] = {
            "requestedModel": requested_model,
            "resolvedModel": profile.get("modelName", ""),
            "provider": profile.get("provider", ""),
            "family": GenerationModelKinds.TEXT,
            "mode": "probe",
            "endpointHost": profile.get("endpointHost", ""),
            "checkedAt": self._support.now_iso(),
            "configSource": profile.get("source", ""),
        }
        if not profile.get("ready", True):
            metadata.update(latencyMs=0, messagePreview="text model config missing")
            call_chain.append(
                self._support.call_log(
                    "probe",
                    "probe.config_missing",
                    "error",
                    "",
                    {"source": profile.get("source", "")},
                )
            )
            result = {
                "runId": run_id,
                "kind": GenerationRunKinds.PROBE,
                "ready": False,
                "latencyMs": 0,
                "callChain": call_chain,
                "metadata": metadata,
            }
            return self._support.run_envelope(
                run_id,
                GenerationRunKinds.PROBE,
                request,
                result,
                "resultProbe",
            )

        response = await self._call_text_model(
            profile,
            system_prompt="You are a connectivity probe. Respond with OK.",
            user_prompt="OK",
        )
        metadata.update(
            latencyMs=response["latencyMs"],
            endpointHost=response["endpointHost"],
            messagePreview=self._support.truncate_text(response["text"], 80),
            providerRequest=response["providerRequest"],
            providerResponse=response["providerResponse"],
            providerHttpStatus=response["httpStatus"],
            providerInteraction=text_provider_interaction("probe", response),
        )
        call_chain.append(
            self._support.call_log(
                "probe",
                "probe.completed",
                "success",
                "",
                {"latencyMs": response["latencyMs"], "responsesApi": response["responsesApi"]},
            )
        )
        result = {
            "runId": run_id,
            "kind": GenerationRunKinds.PROBE,
            "ready": True,
            "latencyMs": response["latencyMs"],
            "callChain": call_chain,
            "metadata": metadata,
        }
        return self._support.run_envelope(
            run_id,
            GenerationRunKinds.PROBE,
            request,
            result,
            "resultProbe",
        )

    async def create_script_run(self, run_id: str, request: dict[str, Any]) -> dict[str, Any]:
        return await self._script_runs.create_script_run(run_id, request)

    async def create_script_adjust_run(self, run_id: str, request: dict[str, Any]) -> dict[str, Any]:
        return await self._script_runs.create_script_adjust_run(run_id, request)
