from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from .embeddings import HashingEmbeddingProvider
from .models import ChunkRecord, SearchQuery, SearchResult, StructuredDocument


class LocalSemanticStore:
    def __init__(
        self,
        root_dir: str | Path,
        *,
        embedding_provider: HashingEmbeddingProvider | None = None,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root_dir / "semantic_store.sqlite3"
        self.embedding_provider = embedding_provider or HashingEmbeddingProvider()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    doc_type TEXT NOT NULL,
                    doc_type_source TEXT NOT NULL,
                    page_count INTEGER NOT NULL,
                    ocr_provider TEXT NOT NULL,
                    full_text TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    doc_type TEXT NOT NULL,
                    page_start INTEGER NOT NULL,
                    page_end INTEGER NOT NULL,
                    block_type TEXT NOT NULL,
                    section_title TEXT,
                    text TEXT NOT NULL,
                    keywords_json TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(document_id)
                );

                CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id);
                CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(doc_type);
                CREATE INDEX IF NOT EXISTS idx_chunks_project ON chunks(project_id);
                CREATE INDEX IF NOT EXISTS idx_chunks_doc_type ON chunks(doc_type);
                CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
                """
            )

    def upsert_document(self, document: StructuredDocument) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO documents (
                    document_id, project_id, source_file, source_path, doc_type, doc_type_source,
                    page_count, ocr_provider, full_text, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    project_id=excluded.project_id,
                    source_file=excluded.source_file,
                    source_path=excluded.source_path,
                    doc_type=excluded.doc_type,
                    doc_type_source=excluded.doc_type_source,
                    page_count=excluded.page_count,
                    ocr_provider=excluded.ocr_provider,
                    full_text=excluded.full_text,
                    metadata_json=excluded.metadata_json
                """,
                (
                    document.document_id,
                    document.project_id,
                    document.source_file,
                    document.source_path,
                    document.doc_type,
                    document.doc_type_source,
                    document.page_count,
                    document.ocr_provider,
                    document.full_text,
                    json.dumps(document.metadata, ensure_ascii=False),
                    now,
                ),
            )

    def replace_chunks(self, document_id: str, chunks: list[ChunkRecord]) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            connection.executemany(
                """
                INSERT INTO chunks (
                    chunk_id, project_id, document_id, source_file, source_path, doc_type,
                    page_start, page_end, block_type, section_title, text, keywords_json,
                    embedding_json, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk.chunk_id,
                        chunk.project_id,
                        chunk.document_id,
                        chunk.source_file,
                        chunk.source_path,
                        chunk.doc_type,
                        chunk.page_start,
                        chunk.page_end,
                        chunk.block_type,
                        chunk.section_title,
                        chunk.text,
                        json.dumps(chunk.keywords, ensure_ascii=False),
                        json.dumps(chunk.embedding, ensure_ascii=False),
                        json.dumps(chunk.metadata, ensure_ascii=False),
                        now,
                    )
                    for chunk in chunks
                ],
            )

    def search(self, query: SearchQuery) -> list[SearchResult]:
        rows = self._load_candidate_rows(query.project_id, query.required_doc_types)
        if not rows:
            return []

        semantic_vectors = self.embedding_provider.embed_many(query.semantic_queries)
        scored_results: list[SearchResult] = []
        for row in rows:
            text = row["text"]
            embedding = json.loads(row["embedding_json"])
            keyword_score = self._compute_keyword_score(text, query.keywords)
            semantic_score = self._compute_semantic_score(embedding, semantic_vectors)
            retrieval_score = self._blend_scores(keyword_score, semantic_score)
            if retrieval_score <= 0:
                continue
            scored_results.append(
                SearchResult(
                    chunk_id=row["chunk_id"],
                    document_id=row["document_id"],
                    source_file=row["source_file"],
                    source_path=row["source_path"],
                    doc_type=row["doc_type"],
                    page_start=int(row["page_start"]),
                    page_end=int(row["page_end"]),
                    section_title=row["section_title"],
                    block_type=row["block_type"],
                    text=text,
                    retrieval_score=retrieval_score,
                    keyword_score=keyword_score,
                    semantic_score=semantic_score,
                    metadata=json.loads(row["metadata_json"]),
                )
            )

        scored_results.sort(key=lambda item: item.retrieval_score, reverse=True)
        return scored_results[: query.top_k]

    def list_documents(self, project_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT document_id, project_id, source_file, source_path, doc_type, doc_type_source,
                       page_count, ocr_provider
                FROM documents
                WHERE project_id = ?
                ORDER BY source_file
                """,
                (project_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def _load_candidate_rows(self, project_id: str, required_doc_types: list[str]) -> list[sqlite3.Row]:
        sql = [
            """
            SELECT chunk_id, document_id, source_file, source_path, doc_type, page_start, page_end,
                   block_type, section_title, text, embedding_json, metadata_json
            FROM chunks
            WHERE project_id = ?
            """
        ]
        params: list[object] = [project_id]
        if required_doc_types:
            placeholders = ", ".join("?" for _ in required_doc_types)
            sql.append(f"AND doc_type IN ({placeholders})")
            params.extend(required_doc_types)
        with self._connect() as connection:
            return connection.execute("\n".join(sql), params).fetchall()

    @staticmethod
    def _compute_keyword_score(text: str, keywords: list[str]) -> float:
        if not keywords:
            return 0.0
        haystack = text.lower()
        matched = 0
        for keyword in keywords:
            if keyword.lower() in haystack:
                matched += 1
        return matched / max(len(keywords), 1)

    def _compute_semantic_score(self, embedding: list[float], semantic_vectors: list[list[float]]) -> float:
        if not semantic_vectors:
            return 0.0
        return max(
            self.embedding_provider.cosine_similarity(embedding, semantic_vector)
            for semantic_vector in semantic_vectors
        )

    @staticmethod
    def _blend_scores(keyword_score: float, semantic_score: float) -> float:
        if keyword_score == 0 and semantic_score == 0:
            return 0.0
        if keyword_score == 0:
            return semantic_score
        if semantic_score == 0:
            return keyword_score
        return (0.35 * keyword_score) + (0.65 * semantic_score)
