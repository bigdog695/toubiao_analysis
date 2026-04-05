from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .doc_types import load_doc_type_catalog, suggest_doc_type
from .embeddings import HashingEmbeddingProvider, tokenize
from .models import ChunkRecord, IngestReport, IngestedDocumentReport
from .ocr_adapter import structured_document_from_ocr
from .runtime import build_ocr_runner
from .store import LocalSemanticStore


def ingest_pdfs(
    *,
    pdf_paths: list[str | Path],
    project_id: str,
    store_dir: str | Path,
    model_path: str | Path = "zhaobiao_file_model.json",
    doc_type_assignments: dict[str, str] | None = None,
    ocr_payloads: dict[str, Any] | None = None,
    run_ocr_func: Callable[[str | Path], Any] | None = None,
    runtime_mode: str = "mock",
    mock_ocr_dir: str | Path | None = None,
    mock_ocr_file_map: dict[str, str] | None = None,
    max_chars_per_chunk: int = 1200,
    overlap_chars: int = 150,
) -> IngestReport:
    store = LocalSemanticStore(store_dir, embedding_provider=HashingEmbeddingProvider())
    report = IngestReport(project_id=project_id, store_dir=str(Path(store_dir).resolve()))
    doc_type_catalog = load_doc_type_catalog(model_path)
    assignments = normalize_doc_type_assignments(doc_type_assignments or {})
    ocr_runner = run_ocr_func or build_ocr_runner(
        runtime_mode=runtime_mode,
        mock_ocr_dir=mock_ocr_dir,
        mock_ocr_file_map=mock_ocr_file_map,
    )

    for pdf_path in pdf_paths:
        path = Path(pdf_path)
        source_file = path.name
        assignment_key = path.resolve().as_posix().lower()
        basename_key = path.name.lower()

        try:
            ocr_payload = (
                ocr_payloads.get(source_file)
                if ocr_payloads and source_file in ocr_payloads
                else ocr_runner(path)
            )
            full_text = extract_full_text(ocr_payload)
            explicit_doc_type = assignments.get(assignment_key) or assignments.get(basename_key)
            if explicit_doc_type:
                doc_type = explicit_doc_type
                doc_type_source = "manual"
            else:
                doc_type, doc_type_source = suggest_doc_type(
                    source_file,
                    full_text,
                    allowed_doc_types=doc_type_catalog,
                )

            document = structured_document_from_ocr(
                project_id=project_id,
                file_path=path,
                doc_type=doc_type,
                doc_type_source=doc_type_source,
                ocr_payload=ocr_payload,
            )
            chunks = build_chunks(
                document=document,
                max_chars_per_chunk=max_chars_per_chunk,
                overlap_chars=overlap_chars,
                embedding_provider=store.embedding_provider,
            )
            store.upsert_document(document)
            store.replace_chunks(document.document_id, chunks)
            report.documents.append(
                IngestedDocumentReport(
                    source_file=document.source_file,
                    source_path=document.source_path,
                    doc_type=document.doc_type,
                    doc_type_source=document.doc_type_source,
                    page_count=document.page_count,
                    chunk_count=len(chunks),
                )
            )
        except Exception as exc:  # noqa: BLE001
            report.errors.append(
                {
                    "source_file": source_file,
                    "source_path": str(path.resolve()),
                    "error": str(exc),
                }
            )
    return report


def normalize_doc_type_assignments(assignments: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in assignments.items():
        path = Path(key)
        normalized[str(path).lower()] = value
        normalized[path.as_posix().lower()] = value
        normalized[str(path.resolve()).lower()] = value
        normalized[path.resolve().as_posix().lower()] = value
        normalized[path.name.lower()] = value
    return normalized


def extract_full_text(ocr_payload: Any) -> str:
    if hasattr(ocr_payload, "full_text"):
        return str(ocr_payload.full_text)
    if hasattr(ocr_payload, "to_dict"):
        payload = ocr_payload.to_dict()
        return str(payload.get("full_text", ""))
    if isinstance(ocr_payload, dict):
        return str(ocr_payload.get("full_text", ""))
    return ""


def build_chunks(
    *,
    document,
    max_chars_per_chunk: int,
    overlap_chars: int,
    embedding_provider: HashingEmbeddingProvider,
) -> list[ChunkRecord]:
    chunks: list[ChunkRecord] = []
    sequence = 1
    for block in document.blocks:
        for chunk_text in split_text(block.text, max_chars_per_chunk, overlap_chars):
            if not chunk_text.strip():
                continue
            chunk_id = f"{document.document_id}-c{sequence:05d}"
            keywords = sorted(set(tokenize(chunk_text)))[:32]
            chunks.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    project_id=document.project_id,
                    document_id=document.document_id,
                    source_file=document.source_file,
                    source_path=document.source_path,
                    doc_type=document.doc_type,
                    page_start=block.page_number,
                    page_end=block.page_number,
                    block_type=block.block_type,
                    section_title=block.section_title,
                    text=chunk_text,
                    keywords=keywords,
                    embedding=embedding_provider.embed_text(chunk_text),
                    metadata={"block_metadata": block.metadata},
                )
            )
            sequence += 1

    if chunks:
        return chunks

    fallback_text = document.full_text.strip()
    if not fallback_text:
        return []

    for chunk_text in split_text(fallback_text, max_chars_per_chunk, overlap_chars):
        chunk_id = f"{document.document_id}-c{sequence:05d}"
        keywords = sorted(set(tokenize(chunk_text)))[:32]
        chunks.append(
            ChunkRecord(
                chunk_id=chunk_id,
                project_id=document.project_id,
                document_id=document.document_id,
                source_file=document.source_file,
                source_path=document.source_path,
                doc_type=document.doc_type,
                page_start=1,
                page_end=max(document.page_count, 1),
                block_type="document",
                section_title=None,
                text=chunk_text,
                keywords=keywords,
                embedding=embedding_provider.embed_text(chunk_text),
                metadata={},
            )
        )
        sequence += 1
    return chunks


def split_text(text: str, max_chars_per_chunk: int, overlap_chars: int) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []
    if len(cleaned) <= max_chars_per_chunk:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    text_length = len(cleaned)
    while start < text_length:
        end = min(start + max_chars_per_chunk, text_length)
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_length:
            break
        start = max(end - overlap_chars, start + 1)
    return chunks
