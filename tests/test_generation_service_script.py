from __future__ import annotations

from typing import Any

import pytest

from backend.services.generation_service import GenerationRunFactory

pytestmark = pytest.mark.service


class _ScriptSupport:
    def __init__(self, tmp_path) -> None:
        self._tmp_path = tmp_path

    def nested_value(self, payload: dict[str, Any], parent_key: str, child_key: str, default: str = "") -> str:
        parent = payload.get(parent_key, {})
        if not isinstance(parent, dict):
            return default
        value = parent.get(child_key, default)
        return str(value) if value is not None else default

    def required_model(self, value: str, field_name: str, label: str) -> str:
        if value.strip():
            return value.strip()
        raise ValueError(f"missing {field_name}")

    def strip_markdown_fence(self, text: str) -> str:
        value = text.strip()
        if not value.startswith("```"):
            return value
        first_break = value.find("\n")
        last_fence = value.rfind("```")
        return value[first_break + 1 : last_fence].strip()

    def call_log(
        self,
        stage: str,
        event: str,
        status: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "stage": stage,
            "event": event,
            "status": status,
            "message": message,
            "details": details or {},
        }

    def write_text_artifact(
        self,
        run_id: str,
        request: dict[str, Any],
        file_name: str,
        content: str,
    ) -> dict[str, str]:
        path = self._tmp_path / file_name
        path.write_text(content, encoding="utf-8")
        return {"absolutePath": str(path), "publicUrl": f"/storage/tasks/{run_id}/{file_name}"}

    def build_model_info(
        self,
        profile: dict[str, Any],
        requested_model: str,
        media_kind: str,
        response: dict[str, Any] | None,
        source_tag: str,
    ) -> dict[str, Any]:
        return {
            "requestedModel": requested_model,
            "resolvedModel": profile.get("modelName", ""),
            "mediaKind": media_kind,
            "source": source_tag,
            "responseId": response.get("responseId", "") if response else "",
        }

    def run_envelope(
        self,
        run_id: str,
        kind: str,
        request: dict[str, Any],
        result: dict[str, Any],
        specific_result_key: str,
        status: str = "SUCCEEDED",
    ) -> dict[str, Any]:
        return {
            "id": run_id,
            "kind": kind,
            "status": status,
            "result": result,
            specific_result_key: result,
        }


class _PromptResolver:
    def system_prompt(self, category: str, name: str) -> str:
        return f"{category}:{name}"


class _SinglePassScriptFactory(GenerationRunFactory):
    def __init__(self, support: _ScriptSupport) -> None:
        super().__init__(
            support=support,
            config_resolver=object(),
            text_provider=object(),
            prompt_resolver=_PromptResolver(),
            image_providers=[],
            video_provider=object(),
        )
        self.calls: list[dict[str, str]] = []

    def _resolve_text_profile(self, requested_model: str, user_id: int | None = None) -> dict[str, Any]:
        return {
            "requestedModel": requested_model,
            "modelName": requested_model,
            "provider": "openai",
            "endpointHost": "api.openai.test",
            "source": "test",
        }

    async def _call_text_model(
        self,
        profile_dict: dict[str, Any],
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        self.calls.append({"systemPrompt": system_prompt, "userPrompt": user_prompt})
        return {
            "text": "【 角色 】\n- 阿明：修表师\n\n【 分镜 】\n| 镜头 | 画面 | 时长 |\n| --- | --- | --- |\n| 1 | 雨夜修表店亮起灯。 | 5 |",
            "modelName": profile_dict.get("modelName", ""),
            "latencyMs": 123,
            "endpointHost": profile_dict.get("endpointHost", ""),
            "providerRequest": {"model": profile_dict.get("modelName", "")},
            "providerResponse": {"id": "resp_draft"},
            "httpStatus": 200,
            "responseId": "resp_draft",
            "responsesApi": True,
        }


@pytest.mark.asyncio
async def test_create_script_run_uses_single_text_model_pass(tmp_path) -> None:
    factory = _SinglePassScriptFactory(_ScriptSupport(tmp_path))

    run = await factory.create_script_run(
        "run_script_1",
        {
            "input": {"text": "雨夜里，修表师收到一块停在十年前的怀表。"},
            "model": {"textAnalysisModel": "gpt-5.5"},
            "options": {"visualStyle": "电影感"},
        },
    )

    result = run["resultScript"]
    metadata = result["metadata"]

    assert len(factory.calls) == 1
    assert "雨夜里" in factory.calls[0]["userPrompt"]
    assert metadata["scriptGenerationMode"] == "single_pass"
    assert metadata["reviewSkipped"] is True
    assert metadata["reviewApplied"] is False
    assert metadata["draftResponseId"] == "resp_draft"
    assert metadata["reviewResponseId"] == ""
    assert metadata["finalResponseId"] == "resp_draft"
    assert [item["step"] for item in metadata["providerInteractions"]] == ["draft"]
    assert "script.review_requested" not in {item["event"] for item in result["callChain"]}
