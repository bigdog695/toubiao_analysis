from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_AZURE_API_VERSION = "2024-10-21"
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_MODEL = "gpt-4.1-mini"


class RealLLMConfigurationError(RuntimeError):
    pass


class RealLLMRequestError(RuntimeError):
    pass


@dataclass(slots=True)
class RealLLMConfig:
    provider: str
    model: str
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    openai_api_key: str | None = None
    openai_base_url: str = DEFAULT_OPENAI_BASE_URL
    azure_api_key: str | None = None
    azure_endpoint: str | None = None
    azure_deployment: str | None = None
    azure_api_version: str = DEFAULT_AZURE_API_VERSION

    @classmethod
    def from_env(cls) -> "RealLLMConfig":
        provider = os.getenv("LSE_LLM_PROVIDER", "openai").strip().lower()
        timeout_seconds = int(os.getenv("LSE_LLM_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
        model = os.getenv("LSE_LLM_MODEL", os.getenv("OPENAI_MODEL", DEFAULT_MODEL))

        if provider == "openai":
            api_key = os.getenv("LSE_OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
            base_url = os.getenv("LSE_OPENAI_BASE_URL", os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL))
            if not api_key:
                raise RealLLMConfigurationError(
                    "Missing OpenAI API key. Set LSE_OPENAI_API_KEY or OPENAI_API_KEY."
                )
            return cls(
                provider=provider,
                model=model,
                timeout_seconds=timeout_seconds,
                openai_api_key=api_key,
                openai_base_url=base_url.rstrip("/"),
            )

        if provider == "azure_openai":
            api_key = os.getenv("LSE_AZURE_OPENAI_API_KEY", os.getenv("AZURE_OPENAI_API_KEY"))
            endpoint = os.getenv("LSE_AZURE_OPENAI_ENDPOINT", os.getenv("AZURE_OPENAI_ENDPOINT"))
            deployment = os.getenv("LSE_AZURE_OPENAI_DEPLOYMENT", os.getenv("AZURE_OPENAI_DEPLOYMENT"))
            api_version = os.getenv("LSE_AZURE_OPENAI_API_VERSION", os.getenv("AZURE_OPENAI_API_VERSION", DEFAULT_AZURE_API_VERSION))
            if not api_key or not endpoint or not deployment:
                raise RealLLMConfigurationError(
                    "Missing Azure OpenAI configuration. Set API key, endpoint, and deployment."
                )
            return cls(
                provider=provider,
                model=model,
                timeout_seconds=timeout_seconds,
                azure_api_key=api_key,
                azure_endpoint=endpoint.rstrip("/"),
                azure_deployment=deployment,
                azure_api_version=api_version,
            )

        raise RealLLMConfigurationError(f"Unsupported LSE_LLM_PROVIDER: {provider}")


class OpenAICompatibleLLMClient:
    def __init__(self, config: RealLLMConfig | None = None) -> None:
        self.config = config or RealLLMConfig.from_env()

    def score_json(self, prompt: str) -> dict[str, Any]:
        payload = self._build_payload(prompt)
        response_payload = self._post_json(payload)
        content = self._extract_content(response_payload)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RealLLMRequestError(f"Model response was not valid JSON: {content[:500]}") from exc
        if not isinstance(parsed, dict):
            raise RealLLMRequestError("Model JSON response must be an object.")
        return parsed

    def _build_payload(self, prompt: str) -> dict[str, Any]:
        payload = {
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "You are a precise scoring assistant. Always return valid JSON only.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        }
        if self.config.provider == "openai":
            payload["model"] = self.config.model
        return payload

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url=self._build_url(),
            data=body,
            headers=self._build_headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RealLLMRequestError(f"LLM HTTP error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RealLLMRequestError(f"LLM request failed: {exc}") from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RealLLMRequestError(f"LLM response was not valid JSON: {raw[:500]}") from exc
        if not isinstance(payload, dict):
            raise RealLLMRequestError("LLM response root must be a JSON object.")
        return payload

    def _build_url(self) -> str:
        if self.config.provider == "openai":
            return f"{self.config.openai_base_url}/chat/completions"

        if self.config.provider == "azure_openai":
            query = urllib.parse.urlencode({"api-version": self.config.azure_api_version})
            return (
                f"{self.config.azure_endpoint}/openai/deployments/"
                f"{self.config.azure_deployment}/chat/completions?{query}"
            )

        raise RealLLMConfigurationError(f"Unsupported provider: {self.config.provider}")

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        if self.config.provider == "openai":
            headers["Authorization"] = f"Bearer {self.config.openai_api_key}"
            return headers
        if self.config.provider == "azure_openai":
            headers["api-key"] = str(self.config.azure_api_key)
            return headers
        raise RealLLMConfigurationError(f"Unsupported provider: {self.config.provider}")

    @staticmethod
    def _extract_content(response_payload: dict[str, Any]) -> str:
        choices = response_payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RealLLMRequestError("LLM response did not include choices.")
        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") in {"text", "output_text"}:
                    text_value = item.get("text")
                    if isinstance(text_value, str):
                        parts.append(text_value)
            if parts:
                return "\n".join(parts)
        raise RealLLMRequestError("LLM response did not include textual message content.")
