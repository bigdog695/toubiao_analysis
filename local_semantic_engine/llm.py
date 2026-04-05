from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any, Protocol


class LLMClient(Protocol):
    def score_json(self, prompt: str) -> dict[str, Any]:
        ...


class FunctionLLMClient:
    def __init__(self, fn: Callable[[str], dict[str, Any]]) -> None:
        self._fn = fn

    def score_json(self, prompt: str) -> dict[str, Any]:
        return self._fn(prompt)


class DryRunLLMClient:
    def score_json(self, prompt: str) -> dict[str, Any]:
        return {
            "score": 0.0,
            "decision": "insufficient_evidence",
            "reasoning": "Dry-run client does not call a real model.",
            "confidence": 0.0,
            "manual_review_required": True,
            "matched_evidence_spans": [],
        }


class MockHeuristicLLMClient:
    def score_json(self, prompt: str) -> dict[str, Any]:
        item_name = _extract_scalar(prompt, "评分项名称")
        decision_mode = _extract_scalar(prompt, "决策模式")
        max_score = _extract_float(_extract_scalar(prompt, "最高分"), 0.0)
        score_logic = _extract_json_section(prompt, "评分逻辑")
        evidence_chunks = _extract_json_section(prompt, "证据chunks")
        if not isinstance(evidence_chunks, list):
            evidence_chunks = []

        if not evidence_chunks:
            return {
                "score": 0.0,
                "decision": "insufficient_evidence",
                "reasoning": f"Mock scoring found no evidence for {item_name}.",
                "confidence": 0.0,
                "manual_review_required": True,
                "matched_evidence_spans": [],
            }

        matched_evidence_spans = [
            {
                "chunk_id": chunk.get("chunk_id", ""),
                "source_file": chunk.get("source_file", ""),
                "page_start": chunk.get("page_start", 0),
                "page_end": chunk.get("page_end", 0),
                "quote": str(chunk.get("text", ""))[:160],
            }
            for chunk in evidence_chunks[:2]
        ]
        avg_retrieval = sum(float(chunk.get("retrieval_score", 0.0)) for chunk in evidence_chunks) / len(evidence_chunks)
        evidence_text = "\n".join(str(chunk.get("text", "")) for chunk in evidence_chunks)

        if decision_mode == "hybrid_rule_rag":
            return self._score_hybrid_rule_rag(
                item_name=item_name,
                max_score=max_score,
                score_logic=score_logic if isinstance(score_logic, dict) else {},
                evidence_text=evidence_text,
                avg_retrieval=avg_retrieval,
                matched_evidence_spans=matched_evidence_spans,
            )

        return self._score_rubric(
            item_name=item_name,
            max_score=max_score,
            score_logic=score_logic if isinstance(score_logic, dict) else {},
            avg_retrieval=avg_retrieval,
            matched_evidence_spans=matched_evidence_spans,
        )

    def _score_hybrid_rule_rag(
        self,
        *,
        item_name: str,
        max_score: float,
        score_logic: dict[str, Any],
        evidence_text: str,
        avg_retrieval: float,
        matched_evidence_spans: list[dict[str, Any]],
    ) -> dict[str, Any]:
        logic_type = score_logic.get("type")
        if logic_type == "binary_full_score":
            passed = avg_retrieval >= 0.45
            score = float(score_logic.get("full_score", max_score if passed else 0.0)) if passed else 0.0
            return {
                "score": min(score, max_score),
                "decision": "pass" if passed else "fail",
                "reasoning": f"Mock binary scoring for {item_name} used average retrieval {avg_retrieval:.2f}.",
                "confidence": min(max(avg_retrieval, 0.2), 0.95),
                "manual_review_required": avg_retrieval < 0.6,
                "matched_evidence_spans": matched_evidence_spans,
            }

        if logic_type == "tiered_capped_score":
            lowered = evidence_text.lower()
            score = 0.0
            reason = "No award level markers matched."
            if "国家级" in evidence_text or "national" in lowered:
                score = float(score_logic.get("tiers", [{}])[0].get("score", max_score))
                reason = "Matched national-level award wording."
            elif "省级" in evidence_text or "provincial" in lowered:
                tiers = score_logic.get("tiers", [{}, {}])
                score = float(tiers[1].get("score", max_score * 0.8)) if len(tiers) > 1 else max_score * 0.8
                reason = "Matched provincial-level award wording."
            elif "市级" in evidence_text or "地市级" in evidence_text or "city" in lowered:
                tiers = score_logic.get("tiers", [{}, {}, {}])
                score = float(tiers[2].get("score", max_score * 0.6)) if len(tiers) > 2 else max_score * 0.6
                reason = "Matched city-level award wording."
            decision = "pass" if score > 0 else "partial"
            return {
                "score": min(score, max_score),
                "decision": decision,
                "reasoning": f"Mock tiered scoring for {item_name}. {reason}",
                "confidence": min(max(avg_retrieval, 0.3), 0.9),
                "manual_review_required": score == 0.0,
                "matched_evidence_spans": matched_evidence_spans,
            }

        return {
            "score": 0.0,
            "decision": "insufficient_evidence",
            "reasoning": f"Mock client does not understand score_logic.type={logic_type!r}.",
            "confidence": 0.2,
            "manual_review_required": True,
            "matched_evidence_spans": matched_evidence_spans,
        }

    def _score_rubric(
        self,
        *,
        item_name: str,
        max_score: float,
        score_logic: dict[str, Any],
        avg_retrieval: float,
        matched_evidence_spans: list[dict[str, Any]],
    ) -> dict[str, Any]:
        rubric_levels = score_logic.get("rubric_levels", [])
        if not rubric_levels:
            return {
                "score": 0.0,
                "decision": "insufficient_evidence",
                "reasoning": f"Mock rubric scoring for {item_name} found no rubric_levels.",
                "confidence": 0.2,
                "manual_review_required": True,
                "matched_evidence_spans": matched_evidence_spans,
            }

        if avg_retrieval >= 0.75:
            chosen = rubric_levels[0]
            decision = "pass"
        elif avg_retrieval >= 0.45 and len(rubric_levels) > 1:
            chosen = rubric_levels[1]
            decision = "partial"
        else:
            chosen = rubric_levels[-1]
            decision = "partial" if avg_retrieval > 0.2 else "insufficient_evidence"

        score_range = chosen.get("score_range", [0.0, 0.0])
        if not isinstance(score_range, list) or len(score_range) != 2:
            score = 0.0
        else:
            score = round((float(score_range[0]) + float(score_range[1])) / 2.0, 4)

        return {
            "score": min(score, max_score),
            "decision": decision,
            "reasoning": (
                f"Mock rubric scoring for {item_name} chose level {chosen.get('label', 'unknown')} "
                f"from average retrieval {avg_retrieval:.2f}."
            ),
            "confidence": min(max(avg_retrieval, 0.25), 0.92),
            "manual_review_required": avg_retrieval < 0.55,
            "matched_evidence_spans": matched_evidence_spans,
        }


def _extract_scalar(prompt: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}:\s*(.+)", prompt)
    return match.group(1).strip() if match else ""


def _extract_float(value: str, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _extract_json_section(prompt: str, label: str) -> Any:
    marker = f"{label}:"
    start = prompt.find(marker)
    if start < 0:
        return {}

    decoder = json.JSONDecoder()
    content_start = start + len(marker)
    same_line_end = prompt.find("\n", content_start)
    if same_line_end < 0:
        same_line_end = len(prompt)
    same_line = prompt[content_start:same_line_end].strip()
    if same_line and same_line[0] in "[{":
        try:
            value, _ = decoder.raw_decode(same_line)
            return value
        except json.JSONDecodeError:
            pass

    scan_start = same_line_end + 1 if same_line_end < len(prompt) else content_start
    for index in range(scan_start, len(prompt)):
        char = prompt[index]
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(prompt[index:])
            return value
        except json.JSONDecodeError:
            continue
    return {}
