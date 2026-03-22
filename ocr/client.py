from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import load_default_env
from .schemas import OCRBlock, OCRResult


DEFAULT_ENDPOINT = "ocr-api.cn-hangzhou.aliyuncs.com"
DEFAULT_IMAGE_TYPE = "Advanced"
DEFAULT_PROVIDER = "aliyun-recognize-all-text"
MAX_BINARY_SIZE_BYTES = 10 * 1024 * 1024
SUPPORTED_FILE_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".gif",
    ".tiff",
    ".webp",
}


class OCRConfigurationError(RuntimeError):
    pass


class OCRInputError(ValueError):
    pass


@dataclass(slots=True)
class OCRConfig:
    access_key_id: str
    access_key_secret: str
    endpoint: str = DEFAULT_ENDPOINT
    security_token: str | None = None
    connect_timeout_ms: int = 10000
    read_timeout_ms: int = 30000

    @classmethod
    def from_env(cls) -> "OCRConfig":
        load_default_env()
        access_key_id = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID")
        access_key_secret = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
        endpoint = os.getenv("ALIYUN_OCR_ENDPOINT", DEFAULT_ENDPOINT)
        security_token = os.getenv("ALIBABA_CLOUD_SECURITY_TOKEN")

        if not access_key_id or not access_key_secret:
            raise OCRConfigurationError(
                "Missing Aliyun OCR credentials. Set ALIBABA_CLOUD_ACCESS_KEY_ID "
                "and ALIBABA_CLOUD_ACCESS_KEY_SECRET in ocr/.env or the shell environment."
            )

        return cls(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint=endpoint,
            security_token=security_token,
        )


class AliyunOCRClient:
    MAX_BINARY_SIZE_BYTES = MAX_BINARY_SIZE_BYTES

    def __init__(self, config: OCRConfig | None = None) -> None:
        self.config = config or OCRConfig.from_env()
        self._sdk_client = None

    def recognize_file(
        self,
        file_path: str | Path,
        *,
        image_type: str = DEFAULT_IMAGE_TYPE,
        page_number: int = 1,
        output_table: bool = True,
        output_char_info: bool = False,
        output_row: bool = True,
        output_paragraph: bool = True,
        output_coordinate: str = "rectangle",
        output_oricoord: bool = False,
    ) -> OCRResult:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"OCR input file does not exist: {path}")
        self._validate_file_input(path, page_number)

        request = self._build_request(
            body=path.read_bytes(),
            image_type=image_type,
            page_number=page_number,
            output_table=output_table,
            output_char_info=output_char_info,
            output_row=output_row,
            output_paragraph=output_paragraph,
            output_coordinate=output_coordinate,
            output_oricoord=output_oricoord,
        )
        response = self._get_sdk_client().recognize_all_text(request)
        return self._normalize_response(
            response=response,
            document_id=path.stem,
            page_number=page_number,
            image_type=image_type,
        )

    def recognize_url(
        self,
        url: str,
        *,
        document_id: str = "remote_document",
        image_type: str = DEFAULT_IMAGE_TYPE,
        page_number: int = 1,
        output_table: bool = True,
        output_char_info: bool = False,
        output_row: bool = True,
        output_paragraph: bool = True,
        output_coordinate: str = "rectangle",
        output_oricoord: bool = False,
    ) -> OCRResult:
        self._validate_url_input(url, page_number)
        request = self._build_request(
            url=url,
            image_type=image_type,
            page_number=page_number,
            output_table=output_table,
            output_char_info=output_char_info,
            output_row=output_row,
            output_paragraph=output_paragraph,
            output_coordinate=output_coordinate,
            output_oricoord=output_oricoord,
        )
        response = self._get_sdk_client().recognize_all_text(request)
        return self._normalize_response(
            response=response,
            document_id=document_id,
            page_number=page_number,
            image_type=image_type,
        )

    def _get_sdk_client(self) -> Any:
        if self._sdk_client is None:
            self._sdk_client = self._create_sdk_client()
        return self._sdk_client

    def _create_sdk_client(self) -> Any:
        try:
            from alibabacloud_ocr_api20210707.client import Client as OCRApiClient
            from alibabacloud_tea_openapi import models as open_api_models
        except ImportError as exc:
            raise OCRConfigurationError(
                "Aliyun OCR SDK is not installed. Install dependencies from requirements.txt."
            ) from exc

        config = open_api_models.Config(
            access_key_id=self.config.access_key_id,
            access_key_secret=self.config.access_key_secret,
            endpoint=self.config.endpoint,
            connect_timeout=self.config.connect_timeout_ms,
            read_timeout=self.config.read_timeout_ms,
        )
        if self.config.security_token:
            config.security_token = self.config.security_token
        return OCRApiClient(config)

    def _build_request(
        self,
        *,
        body: bytes | None = None,
        url: str | None = None,
        image_type: str,
        page_number: int,
        output_table: bool,
        output_char_info: bool,
        output_row: bool,
        output_paragraph: bool,
        output_coordinate: str,
        output_oricoord: bool,
    ) -> Any:
        try:
            from alibabacloud_ocr_api20210707 import models as ocr_models
        except ImportError as exc:
            raise OCRConfigurationError(
                "Aliyun OCR SDK is not installed. Install dependencies from requirements.txt."
            ) from exc

        if bool(body) == bool(url):
            raise ValueError("Exactly one of body or url must be provided.")

        advanced_config = ocr_models.RecognizeAllTextRequestAdvancedConfig(
            output_table=output_table,
            output_char_info=output_char_info,
            output_row=output_row,
            output_paragraph=output_paragraph,
        )
        request = ocr_models.RecognizeAllTextRequest(
            type=image_type,
            page_no=page_number,
            body=body,
            url=url,
            output_coordinate=output_coordinate,
            output_oricoord=output_oricoord,
            advanced_config=advanced_config,
        )
        return request

    def _normalize_response(
        self,
        *,
        response: Any,
        document_id: str,
        page_number: int,
        image_type: str,
    ) -> OCRResult:
        response_map = self._to_mapping(response)
        envelope = self._extract_response_envelope(response_map)
        data = self._extract_data(envelope)

        blocks: list[OCRBlock] = []
        for sub_image in data.get("SubImages", []) or []:
            sub_image_id = sub_image.get("SubImageId")
            block_info = sub_image.get("BlockInfo", {}) or {}
            for detail in block_info.get("BlockDetails", []) or []:
                blocks.append(
                    OCRBlock(
                        block_id=f"{document_id}-p{page_number}-s{sub_image_id}-b{detail.get('BlockId', 0)}",
                        text=self._clean_text(detail.get("BlockContent", "")),
                        confidence=self._normalize_confidence(detail.get("BlockConfidence")),
                        bbox=self._rect_to_bbox(detail.get("BlockRect")),
                        points=detail.get("BlockPoints", []) or [],
                        angle=detail.get("BlockAngle"),
                        sub_image_id=sub_image_id,
                        block_type=sub_image.get("Type"),
                    )
                )

        full_text = self._clean_text(data.get("Content", ""))
        if not full_text and blocks:
            full_text = "\n".join(block.text for block in blocks if block.text)

        return OCRResult(
            document_id=document_id,
            page_number=page_number,
            provider=DEFAULT_PROVIDER,
            full_text=full_text,
            blocks=blocks,
            request_id=self._extract_request_id(response_map, envelope),
            image_type=image_type,
            width=data.get("Width"),
            height=data.get("Height"),
            raw_response=response_map,
        )

    @staticmethod
    def _validate_file_input(path: Path, page_number: int) -> None:
        if page_number < 1:
            raise OCRInputError("page_number must be >= 1.")

        extension = path.suffix.lower()
        if extension not in SUPPORTED_FILE_EXTENSIONS:
            raise OCRInputError(
                f"Unsupported OCR file type: {extension or '<none>'}. "
                f"Supported types: {', '.join(sorted(SUPPORTED_FILE_EXTENSIONS))}."
            )

        file_size = path.stat().st_size
        if file_size > MAX_BINARY_SIZE_BYTES:
            raise OCRInputError(
                f"Input file exceeds the 10MB Aliyun OCR limit: {file_size} bytes."
            )

    @staticmethod
    def _validate_url_input(url: str, page_number: int) -> None:
        if page_number < 1:
            raise OCRInputError("page_number must be >= 1.")
        if not url or not url.strip():
            raise OCRInputError("url must be a non-empty string.")

    @staticmethod
    def _normalize_confidence(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value) / 100.0
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _rect_to_bbox(rect: dict[str, Any] | None) -> list[int] | None:
        if not rect:
            return None
        center_x = rect.get("CenterX")
        center_y = rect.get("CenterY")
        width = rect.get("Width")
        height = rect.get("Height")
        if None in (center_x, center_y, width, height):
            return None
        left = int(center_x - width / 2)
        top = int(center_y - height / 2)
        right = int(center_x + width / 2)
        bottom = int(center_y + height / 2)
        return [left, top, right, bottom]

    @staticmethod
    def _clean_text(value: str) -> str:
        return str(value).strip().strip('"')

    @staticmethod
    def _extract_data(response_map: dict[str, Any]) -> dict[str, Any]:
        data = response_map.get("Data", {})
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _extract_response_envelope(response_map: dict[str, Any]) -> dict[str, Any]:
        body = response_map.get("body")
        if isinstance(body, dict):
            return body
        return response_map

    @staticmethod
    def _extract_request_id(response_map: dict[str, Any], envelope: dict[str, Any]) -> str | None:
        return (
            response_map.get("RequestId")
            or envelope.get("RequestId")
            or response_map.get("headers", {}).get("x-acs-request-id")
        )

    @staticmethod
    def _to_mapping(response: Any) -> dict[str, Any]:
        if isinstance(response, dict):
            return response
        if hasattr(response, "to_map"):
            return response.to_map()
        if hasattr(response, "body") and hasattr(response.body, "to_map"):
            return response.body.to_map()
        raise TypeError("Unsupported OCR response type; expected dict or Tea model.")


def recognize_all_text_file(
    file_path: str | Path,
    *,
    image_type: str = DEFAULT_IMAGE_TYPE,
    page_number: int = 1,
    config: OCRConfig | None = None,
) -> dict[str, Any]:
    client = AliyunOCRClient(config=config)
    result = client.recognize_file(
        file_path,
        image_type=image_type,
        page_number=page_number,
    )
    return result.to_dict()
