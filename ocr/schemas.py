from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class OCRBlock:
    block_id: str
    text: str
    confidence: float | None = None
    bbox: list[int] | None = None
    points: list[dict[str, int]] = field(default_factory=list)
    angle: int | None = None
    sub_image_id: int | None = None
    block_type: str | None = None


@dataclass(slots=True)
class OCRResult:
    document_id: str
    page_number: int
    provider: str
    full_text: str
    blocks: list[OCRBlock] = field(default_factory=list)
    request_id: str | None = None
    image_type: str | None = None
    width: int | None = None
    height: int | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blocks"] = [asdict(block) for block in self.blocks]
        return payload


@dataclass(slots=True)
class OCRBatchResult:
    document_id: str
    provider: str
    page_results: list[OCRResult] = field(default_factory=list)
    total_pages: int = 0
    full_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "provider": self.provider,
            "total_pages": self.total_pages,
            "full_text": self.full_text,
            "page_results": [page.to_dict() for page in self.page_results],
        }


@dataclass(slots=True)
class SealPageResult:
    document_id: str
    page_number: int
    provider: str
    source_name: str
    raw_response: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SealBatchResult:
    document_id: str
    provider: str
    total_pages: int = 0
    page_results: list[SealPageResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "provider": self.provider,
            "total_pages": self.total_pages,
            "page_results": [page.to_dict() for page in self.page_results],
        }
