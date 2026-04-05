from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .models import StructuredBlock, StructuredDocument, ensure_path_string


def default_run_ocr(file_path: str | Path) -> Any:
    from ocr.pipeline import recognize_document

    return recognize_document(file_path)


def load_mock_ocr_payload(
    file_path: str | Path,
    *,
    mock_ocr_dir: str | Path | None = None,
    mock_ocr_file_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    path = Path(file_path)
    if mock_ocr_file_map:
        for candidate_key in (
            str(path),
            str(path.resolve()),
            path.as_posix(),
            path.resolve().as_posix(),
            path.name,
            path.stem,
        ):
            if candidate_key in mock_ocr_file_map:
                payload_path = Path(mock_ocr_file_map[candidate_key])
                return json.loads(payload_path.read_text(encoding="utf-8"))

    if mock_ocr_dir is None:
        raise ValueError("mock_ocr_dir is required for mock OCR when no file map is provided.")

    directory = Path(mock_ocr_dir)
    candidates = [
        directory / f"{path.stem}.ocr.json",
        directory / f"{path.name}.ocr.json",
        directory / f"{path.stem}.json",
        directory / f"{path.name}.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))

    raise FileNotFoundError(f"No mock OCR payload found for {path.name} in {directory}")


def normalize_ocr_payload(payload: Any) -> dict[str, Any]:
    if hasattr(payload, "to_dict"):
        return payload.to_dict()
    if isinstance(payload, dict):
        return payload
    raise TypeError(f"Unsupported OCR payload type: {type(payload)!r}")


def structured_document_from_ocr(
    *,
    project_id: str,
    file_path: str | Path,
    doc_type: str,
    doc_type_source: str,
    ocr_payload: Any,
) -> StructuredDocument:
    normalized = normalize_ocr_payload(ocr_payload)
    page_results = normalized.get("page_results", [])
    source_path = ensure_path_string(file_path)
    source_file = Path(file_path).name
    original_document_id = str(normalized.get("document_id") or Path(file_path).stem)
    blocks: list[StructuredBlock] = []

    for page in page_results:
        page_number = int(page.get("page_number", 0) or 0)
        page_blocks = page.get("blocks") or []
        if page_blocks:
            for block in page_blocks:
                text = (block.get("text") or "").strip()
                if not text:
                    continue
                blocks.append(
                    StructuredBlock(
                        page_number=page_number,
                        text=text,
                        block_type=(block.get("block_type") or "paragraph").lower(),
                        confidence=block.get("confidence"),
                        metadata={"ocr_block": block},
                    )
                )
            continue

        full_text = (page.get("full_text") or "").strip()
        if not full_text:
            continue
        for paragraph in split_full_text_to_blocks(full_text):
            blocks.append(
                StructuredBlock(
                    page_number=page_number,
                    text=paragraph,
                    block_type="paragraph",
                )
            )

    full_text = normalized.get("full_text") or "\n\n".join(block.text for block in blocks)
    page_count = int(normalized.get("total_pages") or len(page_results) or 0)
    provider = normalized.get("provider", "unknown")

    return StructuredDocument(
        project_id=project_id,
        document_id=build_scoped_document_id(
            project_id=project_id,
            source_path=source_path,
            original_document_id=original_document_id,
        ),
        source_file=source_file,
        source_path=source_path,
        doc_type=doc_type,
        doc_type_source=doc_type_source,
        page_count=page_count,
        ocr_provider=provider,
        full_text=full_text,
        blocks=blocks,
        metadata={
            "ocr_payload": normalized,
            "original_document_id": original_document_id,
        },
    )


def split_full_text_to_blocks(full_text: str) -> list[str]:
    paragraphs = []
    for paragraph in full_text.replace("\r\n", "\n").split("\n\n"):
        cleaned = "\n".join(line.strip() for line in paragraph.splitlines() if line.strip()).strip()
        if cleaned:
            paragraphs.append(cleaned)
    return paragraphs


def build_scoped_document_id(*, project_id: str, source_path: str, original_document_id: str) -> str:
    digest = hashlib.sha1(source_path.encode("utf-8")).hexdigest()[:12]
    safe_project = _slugify(project_id)
    safe_document = _slugify(original_document_id)
    return f"{safe_project}__{safe_document}__{digest}"


def _slugify(value: str) -> str:
    sanitized = "".join(char if char.isalnum() else "_" for char in value.strip())
    sanitized = "_".join(part for part in sanitized.split("_") if part)
    return sanitized[:80] or "document"
