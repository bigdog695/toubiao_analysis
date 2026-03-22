from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests

from .client import OCRConfigurationError, OCRInputError
from .config import load_default_env


SEAL_MARKET_ENDPOINT = "https://stamp.market.alicloudapi.com"
SEAL_MARKET_PATH = "/api/predict/ocr_official_seal"
SEAL_MARKET_PROVIDER = "aliyun-market-official-seal"
SEAL_SUPPORTED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".gif",
    ".tiff",
    ".webp",
}


@dataclass(slots=True)
class SealMarketConfig:
    app_key: str
    app_secret: str
    endpoint: str = SEAL_MARKET_ENDPOINT
    path: str = SEAL_MARKET_PATH
    timeout_seconds: int = 60

    @classmethod
    def from_env(cls) -> "SealMarketConfig":
        load_default_env()
        app_key = os.getenv("ALIYUN_MARKET_SEAL_APP_KEY")
        app_secret = os.getenv("ALIYUN_MARKET_SEAL_APP_SECRET")
        endpoint = os.getenv("ALIYUN_MARKET_SEAL_ENDPOINT", SEAL_MARKET_ENDPOINT)
        path = os.getenv("ALIYUN_MARKET_SEAL_PATH", SEAL_MARKET_PATH)

        if not app_key or not app_secret:
            raise OCRConfigurationError(
                "Missing seal OCR market credentials. Set ALIYUN_MARKET_SEAL_APP_KEY "
                "and ALIYUN_MARKET_SEAL_APP_SECRET in ocr/.env or the shell environment."
            )

        return cls(
            app_key=app_key,
            app_secret=app_secret,
            endpoint=endpoint.rstrip("/"),
            path=path,
        )


class AliyunMarketSealClient:
    def __init__(self, config: SealMarketConfig | None = None) -> None:
        self.config = config or SealMarketConfig.from_env()

    def recognize_file(self, file_path: str | Path) -> dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Seal OCR input file does not exist: {path}")

        extension = path.suffix.lower()
        if extension not in SEAL_SUPPORTED_EXTENSIONS:
            raise OCRInputError(
                f"Unsupported seal OCR file type: {extension or '<none>'}. "
                f"Supported types: {', '.join(sorted(SEAL_SUPPORTED_EXTENSIONS))}."
            )

        image_base64 = base64.b64encode(path.read_bytes()).decode("utf-8")
        return self._post_image_payload(image=image_base64, source_name=path.stem)

    def recognize_url(self, image_url: str, *, source_name: str = "remote_seal") -> dict[str, Any]:
        if not image_url or not image_url.strip():
            raise OCRInputError("image_url must be a non-empty string.")
        return self._post_image_payload(image=image_url.strip(), source_name=source_name)

    def _post_image_payload(self, *, image: str, source_name: str) -> dict[str, Any]:
        body = {"image": image}
        body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers = self._build_headers(body_bytes)

        response = requests.post(
            f"{self.config.endpoint}{self.config.path}",
            data=body_bytes,
            headers=headers,
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        return {
            "provider": SEAL_MARKET_PROVIDER,
            "source_name": source_name,
            "raw_response": payload,
        }

    def recognize_file_safe(self, file_path: str | Path) -> dict[str, Any]:
        try:
            return self.recognize_file(file_path)
        except requests.HTTPError as exc:
            response = exc.response
            raw_payload: dict[str, Any]
            if response is not None:
                try:
                    raw_payload = response.json()
                except ValueError:
                    raw_payload = {"text": response.text}
                raw_payload["_http_status"] = response.status_code
            else:
                raw_payload = {"text": str(exc)}
            return {
                "provider": SEAL_MARKET_PROVIDER,
                "source_name": Path(file_path).stem,
                "raw_response": raw_payload,
                "error": str(exc),
            }

    def _build_headers(self, body_bytes: bytes) -> dict[str, str]:
        accept = "application/json; charset=utf-8"
        content_type = "application/json; charset=utf-8"
        content_md5 = base64.b64encode(hashlib.md5(body_bytes).digest()).decode("utf-8")
        nonce = str(uuid.uuid4())
        timestamp = str(int(time.time() * 1000))

        sign_headers = {
            "x-ca-key": self.config.app_key,
            "x-ca-nonce": nonce,
            "x-ca-signature-method": "HmacSHA256",
            "x-ca-timestamp": timestamp,
        }
        signature_headers = ",".join(sign_headers.keys())
        string_to_sign = self._build_string_to_sign(
            method="POST",
            accept=accept,
            content_md5=content_md5,
            content_type=content_type,
            headers=sign_headers,
            path=self.config.path,
        )
        signature = base64.b64encode(
            hmac.new(
                self.config.app_secret.encode("utf-8"),
                string_to_sign.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode("utf-8")

        headers = {
            "Accept": accept,
            "Content-Type": content_type,
            "Content-MD5": content_md5,
            "X-Ca-Key": self.config.app_key,
            "X-Ca-Nonce": nonce,
            "X-Ca-Signature-Method": "HmacSHA256",
            "X-Ca-Timestamp": timestamp,
            "X-Ca-Signature-Headers": signature_headers,
            "X-Ca-Signature": signature,
        }
        return headers

    @staticmethod
    def _build_string_to_sign(
        *,
        method: str,
        accept: str,
        content_md5: str,
        content_type: str,
        headers: dict[str, str],
        path: str,
        query: dict[str, str] | None = None,
    ) -> str:
        canonical_headers = "\n".join(
            f"{key}:{headers[key]}" for key in sorted(headers.keys(), key=str.lower)
        )
        path_and_params = path
        if query:
            path_and_params = f"{path}?{urlencode(sorted(query.items()))}"
        return "\n".join(
            [
                method.upper(),
                accept,
                content_md5,
                content_type,
                "",
                canonical_headers,
                path_and_params,
            ]
        )


def recognize_official_seal_file(
    file_path: str | Path,
    *,
    config: SealMarketConfig | None = None,
) -> dict[str, Any]:
    client = AliyunMarketSealClient(config=config)
    return client.recognize_file(file_path)
