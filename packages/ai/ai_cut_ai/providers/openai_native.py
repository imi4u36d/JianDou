from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import socket
import urllib.error
import urllib.parse
import urllib.request

from ai_cut_shared.config import Settings

from .base import ProviderResult, ResolvedModelTarget
from .openai_compatible import OpenAICompatibleAdapter


class OpenAINativeAdapter(OpenAICompatibleAdapter):
    name = "openai_native"

    def invoke_text(
        self,
        *,
        settings: Settings,
        target: ResolvedModelTarget,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        enable_thinking: bool = False,
        file_input_path: Path | None = None,
        file_input_name: str | None = None,
    ) -> ProviderResult:
        if file_input_path is None:
            return super().invoke_text(
                settings=settings,
                target=target,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                enable_thinking=enable_thinking,
            )
        api_base = str(target.base_url or "").strip().rstrip("/")
        if api_base.endswith("/chat/completions"):
            api_base = api_base[: -len("/chat/completions")]
        elif api_base.endswith("/responses"):
            api_base = api_base[: -len("/responses")]
        uploaded_file_id = self._upload_input_file(
            api_base=api_base,
            api_key=target.api_key,
            source_text_file_path=file_input_path,
            source_text_file_name=file_input_name or file_input_path.name,
            timeout_seconds=float(settings.model.timeout_seconds),
        )
        try:
            body = {
                "model": target.model_name,
                "input": [
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": system_prompt}],
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": user_prompt},
                            {"type": "input_file", "file_id": uploaded_file_id},
                        ],
                    },
                ],
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            payload, raw = self._request_json(
                endpoint=f"{api_base}/responses",
                api_key=target.api_key,
                body=body,
                timeout_seconds=float(settings.model.timeout_seconds),
            )
            return ProviderResult(
                payload=payload,
                raw_text=raw,
                endpoint=f"{api_base}/responses",
                mode="responses_file_input",
            )
        finally:
            self._delete_input_file(
                api_base=api_base,
                api_key=target.api_key,
                file_id=uploaded_file_id,
                timeout_seconds=float(settings.model.timeout_seconds),
            )

    def _upload_input_file(
        self,
        *,
        api_base: str,
        api_key: str,
        source_text_file_path: Path,
        source_text_file_name: str,
        timeout_seconds: float,
    ) -> str:
        boundary = "----AICutOpenAIFileBoundary"
        file_bytes = source_text_file_path.read_bytes()
        parts = [
            f"--{boundary}\r\n".encode("utf-8"),
            b'Content-Disposition: form-data; name="purpose"\r\n\r\n',
            b"user_data\r\n",
            f"--{boundary}\r\n".encode("utf-8"),
            (
                f'Content-Disposition: form-data; name="file"; filename="{source_text_file_name}"\r\n'
                "Content-Type: text/plain\r\n\r\n"
            ).encode("utf-8"),
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
        request = urllib.request.Request(
            f"{api_base}/files",
            data=b"".join(parts),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
        payload = self._request_raw(request=request, timeout_seconds=timeout_seconds)
        file_id = str(payload.get("id") or "").strip()
        if not file_id:
            raise RuntimeError("openai file upload missing file id")
        return file_id

    def _delete_input_file(
        self,
        *,
        api_base: str,
        api_key: str,
        file_id: str,
        timeout_seconds: float,
    ) -> None:
        if not file_id:
            return
        request = urllib.request.Request(
            f"{api_base}/files/{urllib.parse.quote(file_id)}",
            method="DELETE",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        try:
            self._request_raw(request=request, timeout_seconds=timeout_seconds)
        except Exception:
            return

    def _request_raw(self, *, request: urllib.request.Request, timeout_seconds: float) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="ignore")
        except (TimeoutError, socket.timeout) as exc:
            raise RuntimeError(f"model request timed out: {exc}") from exc
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="ignore")
            except Exception:
                detail = ""
            raise RuntimeError(f"model request http error: {exc.code} {detail[:400]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"model request network error: {exc}") from exc
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        return payload
