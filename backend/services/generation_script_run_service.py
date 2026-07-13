"""Script generation and adjustment run orchestration."""

from __future__ import annotations

from typing import Any

from backend.domain.generation_run import GenerationRunKinds
from backend.services.generation_payloads import build_script_adjust_user_prompt, build_script_user_prompt
from backend.services.generation_run_support import GenerationRunSupport
from backend.services.generation_text_run_values import (
    invalid_storyboard_reason,
    request_metadata,
    text_provider_interaction,
    user_id_from_request,
)


class GenerationScriptRunService:
    def __init__(
        self,
        support: GenerationRunSupport,
        prompt_resolver: Any,
        resolve_text_profile: Any,
        call_text_model: Any,
    ) -> None:
        self._support = support
        self._prompt_resolver = prompt_resolver
        self._resolve_text_profile = resolve_text_profile
        self._call_text_model = call_text_model

    async def create_script_run(self, run_id: str, request: dict[str, Any]) -> dict[str, Any]:
        source_text = self._support.nested_value(request, "input", "text", "")
        requested_model = self._required_text_model(request)
        profile = self._resolve_text_profile(requested_model, user_id_from_request(request))
        if not source_text.strip():
            raise ValueError("")

        prompt = build_script_user_prompt(source_text)
        system_prompt = self._prompt_resolver.system_prompt("script", "short_drama_script")
        response = await self._call_text_model(profile, system_prompt=system_prompt, user_prompt=prompt)
        script_markdown = self._support.strip_markdown_fence(response["text"])
        call_chain = [
            self._support.call_log(
                "script",
                "script.requested",
                "success",
                "",
                {
                    "provider": profile.get("provider", ""),
                    "modelName": profile.get("modelName", ""),
                    "endpointHost": response["endpointHost"],
                },
            ),
            self._support.call_log(
                "script",
                "script.draft_completed",
                "success",
                "",
                {
                    "latencyMs": response["latencyMs"],
                    "responsesApi": response["responsesApi"],
                    "responseId": response["responseId"],
                },
            ),
            self._support.call_log(
                "script",
                "script.completed",
                "success",
                "",
                {
                    "latencyMs": response["latencyMs"],
                    "responsesApi": response["responsesApi"],
                    "responseId": response["responseId"],
                    "reviewApplied": False,
                    "singlePass": True,
                },
            ),
        ]
        artifact = self._support.write_text_artifact(run_id, request, "script.md", script_markdown)
        model_info = self._support.build_model_info(
            profile,
            requested_model,
            "script",
            response,
            "spring-text-script",
        )
        metadata = {
            "draftScriptMarkdown": script_markdown,
            "scriptMarkdown": script_markdown,
            "reviewApplied": False,
            "draftResponseId": response["responseId"],
            "reviewResponseId": "",
            "finalResponseId": response["responseId"],
            "scriptGenerationMode": "single_pass",
            "reviewSkipped": True,
            "providerInteractions": [text_provider_interaction("draft", response)],
            "providerRequest": response["providerRequest"],
            "providerResponse": response["providerResponse"],
            "providerHttpStatus": response["httpStatus"],
            "fileUrl": artifact["publicUrl"],
            "configSource": profile.get("source", ""),
            **request_metadata(request),
        }
        result = {
            "runId": run_id,
            "kind": GenerationRunKinds.SCRIPT,
            "sourceText": source_text,
            "prompt": prompt,
            "outputFormat": "markdown",
            "scriptMarkdown": script_markdown,
            "markdownPath": artifact["absolutePath"],
            "markdownUrl": artifact["publicUrl"],
            "mimeType": "text/markdown",
            "callChain": call_chain,
            "metadata": metadata,
            "modelInfo": model_info,
        }
        return self._support.run_envelope(
            run_id,
            GenerationRunKinds.SCRIPT,
            request,
            result,
            "resultScript",
        )

    async def create_script_adjust_run(self, run_id: str, request: dict[str, Any]) -> dict[str, Any]:
        source_text = self._support.first_non_blank(
            self._support.nested_value(request, "input", "text", ""),
            self._support.nested_value(request, "input", "sourceText", ""),
        )
        script_markdown = self._support.nested_value(request, "input", "scriptMarkdown", "")
        adjustment_prompt = self._support.nested_value(request, "input", "adjustmentPrompt", "")
        requested_model = self._required_text_model(request)
        profile = self._resolve_text_profile(requested_model, user_id_from_request(request))
        if not script_markdown.strip():
            raise ValueError("")

        prompt = build_script_adjust_user_prompt(source_text, script_markdown, adjustment_prompt)
        system_prompt = self._prompt_resolver.system_prompt("script", "short_drama_script")
        response = await self._call_text_model(profile, system_prompt=system_prompt, user_prompt=prompt)
        call_chain = [
            self._support.call_log(
                "script",
                "script.adjust_requested",
                "success",
                "",
                {
                    "provider": profile.get("provider", ""),
                    "modelName": profile.get("modelName", ""),
                    "endpointHost": response["endpointHost"],
                },
            )
        ]
        adjusted_script = self._support.strip_markdown_fence(response["text"])
        invalid_reason = invalid_storyboard_reason(adjusted_script)
        if invalid_reason:
            call_chain.append(
                self._support.call_log(
                    "script",
                    "script.adjust_invalid",
                    "error",
                    "",
                    {"reason": invalid_reason, "responseId": response["responseId"]},
                )
            )
            raise ValueError(f"  {invalid_reason}")

        adjustment_mode = "self_review" if not adjustment_prompt.strip() else "user_prompt"
        call_chain.append(
            self._support.call_log(
                "script",
                "script.adjust_completed",
                "success",
                "",
                {
                    "latencyMs": response["latencyMs"],
                    "responsesApi": response["responsesApi"],
                    "responseId": response["responseId"],
                    "adjustmentMode": adjustment_mode,
                },
            )
        )
        artifact = self._support.write_text_artifact(run_id, request, "script.md", adjusted_script)
        model_info = self._support.build_model_info(
            profile,
            requested_model,
            "script",
            response,
            "spring-text-script-adjust",
        )
        metadata = {
            "scriptMarkdown": adjusted_script,
            "sourceScriptMarkdown": script_markdown,
            "adjustmentPrompt": adjustment_prompt,
            "adjustmentMode": adjustment_mode,
            "adjustmentResponseId": response["responseId"],
            "providerInteractions": [text_provider_interaction("adjust", response)],
            "providerRequest": response["providerRequest"],
            "providerResponse": response["providerResponse"],
            "providerHttpStatus": response["httpStatus"],
            "fileUrl": artifact["publicUrl"],
            "configSource": profile.get("source", ""),
            **request_metadata(request),
        }
        result = {
            "runId": run_id,
            "kind": GenerationRunKinds.SCRIPT_ADJUST,
            "sourceText": source_text,
            "prompt": prompt,
            "adjustmentPrompt": adjustment_prompt,
            "adjustmentMode": adjustment_mode,
            "outputFormat": "markdown",
            "scriptMarkdown": adjusted_script,
            "markdownPath": artifact["absolutePath"],
            "markdownUrl": artifact["publicUrl"],
            "mimeType": "text/markdown",
            "callChain": call_chain,
            "metadata": metadata,
            "modelInfo": model_info,
        }
        return self._support.run_envelope(
            run_id,
            GenerationRunKinds.SCRIPT_ADJUST,
            request,
            result,
            "resultScript",
        )

    def _required_text_model(self, request: dict[str, Any]) -> str:
        return self._support.required_model(
            self._support.nested_value(request, "model", "textAnalysisModel", ""),
            "textAnalysisModel",
            "",
        )
