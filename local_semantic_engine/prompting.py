from __future__ import annotations

import json

from .models import SearchResult, SemanticScoringItem


def build_semantic_scoring_prompt(
    *,
    item: SemanticScoringItem,
    evidence_chunks: list[SearchResult],
    project_id: str,
) -> str:
    evidence_payload = [
        {
            "chunk_id": chunk.chunk_id,
            "source_file": chunk.source_file,
            "doc_type": chunk.doc_type,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "section_title": chunk.section_title,
            "text": chunk.text,
            "retrieval_score": round(chunk.retrieval_score, 4),
        }
        for chunk in evidence_chunks
    ]
    output_schema = {
        "score": 0.0,
        "decision": "pass|fail|partial|insufficient_evidence",
        "reasoning": "",
        "confidence": 0.0,
        "manual_review_required": False,
        "matched_evidence_spans": [
            {
                "chunk_id": "",
                "source_file": "",
                "page_start": 0,
                "page_end": 0,
                "quote": "",
            }
        ],
    }

    return f"""
你是投标文件评分助手。你只能依据给定证据评分，不允许补充外部知识，不允许猜测。

项目ID: {project_id}
评分项ID: {item.item_id}
评分项名称: {item.item_name}
决策模式: {item.decision_mode}
最高分: {item.max_score}
文档类型限制:
{json.dumps(item.required_doc_types, ensure_ascii=False, indent=2)}
抽取目标:
{json.dumps(item.extraction_targets, ensure_ascii=False, indent=2)}
检索提示:
{json.dumps(item.retrieval_hints, ensure_ascii=False, indent=2)}
评分逻辑:
{json.dumps(item.score_logic, ensure_ascii=False, indent=2)}
LLM任务要求:
{json.dumps(item.llm_task, ensure_ascii=False, indent=2)}

证据chunks:
{json.dumps(evidence_payload, ensure_ascii=False, indent=2)}

输出要求:
1. 必须只输出 JSON。
2. score 必须在 0 到 {item.max_score} 之间。
3. 如果证据不足，decision 必须是 insufficient_evidence，score 应尽量保守。
4. matched_evidence_spans 只能引用提供的 chunk_id。
5. reasoning 必须简洁说明依据。

输出 schema:
{json.dumps(output_schema, ensure_ascii=False, indent=2)}
""".strip()
