from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class StructuredBlock:
    page_number: int
    text: str
    block_type: str = "paragraph"
    section_title: str | None = None
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StructuredDocument:
    project_id: str
    document_id: str
    source_file: str
    source_path: str
    doc_type: str
    doc_type_source: str
    page_count: int
    ocr_provider: str
    full_text: str
    blocks: list[StructuredBlock] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ChunkRecord:
    chunk_id: str
    project_id: str
    document_id: str
    source_file: str
    source_path: str
    doc_type: str
    page_start: int
    page_end: int
    block_type: str
    section_title: str | None
    text: str
    keywords: list[str] = field(default_factory=list)
    embedding: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SearchQuery:
    project_id: str
    required_doc_types: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    semantic_queries: list[str] = field(default_factory=list)
    top_k: int = 5


@dataclass(slots=True)
class SearchResult:
    chunk_id: str
    document_id: str
    source_file: str
    source_path: str
    doc_type: str
    page_start: int
    page_end: int
    section_title: str | None
    block_type: str
    text: str
    retrieval_score: float
    keyword_score: float
    semantic_score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SemanticScoringItem:
    item_id: str
    item_name: str
    decision_mode: str
    bucket_code: str
    category: str
    subcategory: str
    max_score: float
    required_doc_types: list[str] = field(default_factory=list)
    extraction_targets: list[str] = field(default_factory=list)
    retrieval_hints: dict[str, Any] = field(default_factory=dict)
    score_logic: dict[str, Any] = field(default_factory=dict)
    llm_task: dict[str, Any] = field(default_factory=dict)
    raw_item: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SemanticScoreResult:
    item_id: str
    item_name: str
    decision_mode: str
    score: float
    max_score: float
    decision: str
    reasoning: str
    confidence: float
    matched_evidence_spans: list[dict[str, Any]] = field(default_factory=list)
    manual_review_required: bool = False
    raw_model_output: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class IngestedDocumentReport:
    source_file: str
    source_path: str
    doc_type: str
    doc_type_source: str
    page_count: int
    chunk_count: int


@dataclass(slots=True)
class IngestReport:
    project_id: str
    store_dir: str
    documents: list[IngestedDocumentReport] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)


def ensure_path_string(path: str | Path) -> str:
    return str(Path(path).resolve())
