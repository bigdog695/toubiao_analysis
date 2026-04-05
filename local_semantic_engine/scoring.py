from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .llm import LLMClient
from .model_loader import load_scoring_model, load_semantic_scoring_items
from .models import SearchQuery, SemanticScoreResult
from .prompting import build_semantic_scoring_prompt
from .store import LocalSemanticStore


class RuleBasedResult:
    def score_item(self, item: dict[str, Any]) -> dict[str, Any]:
        # TODO(barry): implement rule-based scoring here.
        return {
            "item_id": item.get("item_id"),
            "item_name": item.get("item_name"),
            "score": 0.0,
            "result": "",
            "reason": "",
            "evidence": [],
            "implemented": False,
        }


class PriceScoringResult:
    def score_item(self, item: dict[str, Any]) -> dict[str, Any]:
        # TODO(barry): implement price scoring here.
        return {
            "item_id": item.get("item_id"),
            "item_name": item.get("item_name"),
            "score": 0.0,
            "result": "",
            "reason": "",
            "evidence": [],
            "implemented": False,
        }


class SemanticScoringRunner:
    def __init__(
        self,
        *,
        store: LocalSemanticStore,
        llm_client: LLMClient,
        top_k: int = 5,
    ) -> None:
        self.store = store
        self.llm_client = llm_client
        self.top_k = top_k

    def score_items(self, *, project_id: str, model_path: str) -> dict[str, Any]:
        semantic_items = load_semantic_scoring_items(model_path)
        scoring_model = load_scoring_model(model_path).get("scoring_model", {})
        all_items = scoring_model.get("scoring_items", [])
        semantic_results: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        for item in semantic_items:
            try:
                semantic_results.append(asdict(self.score_item(project_id=project_id, item=item)))
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    {
                        "item_id": item.item_id,
                        "item_name": item.item_name,
                        "error": str(exc),
                    }
                )

        semantic_ids = {item.item_id for item in semantic_items}
        rule_result = RuleBasedResult()
        price_result = PriceScoringResult()
        rule_based_results = [
            rule_result.score_item(item)
            for item in all_items
            if item.get("item_id") not in semantic_ids
        ]
        price_item = scoring_model.get("price_scoring")
        return {
            "semantic_scoring_results": semantic_results,
            "rule_based_results": rule_based_results,
            "price_result": price_result.score_item(price_item) if isinstance(price_item, dict) else None,
            "errors": errors,
        }

    def score_item(self, *, project_id: str, item) -> SemanticScoreResult:
        evidence_chunks = self.store.search(
            SearchQuery(
                project_id=project_id,
                required_doc_types=list(item.required_doc_types),
                keywords=list(item.retrieval_hints.get("keywords", [])),
                semantic_queries=list(item.retrieval_hints.get("semantic_queries", [])),
                top_k=self.top_k,
            )
        )
        if not evidence_chunks:
            return SemanticScoreResult(
                item_id=item.item_id,
                item_name=item.item_name,
                decision_mode=item.decision_mode,
                score=0.0,
                max_score=item.max_score,
                decision="insufficient_evidence",
                reasoning="No evidence chunks were retrieved for this scoring item.",
                confidence=0.0,
                matched_evidence_spans=[],
                manual_review_required=True,
                raw_model_output={},
            )

        prompt = build_semantic_scoring_prompt(
            item=item,
            evidence_chunks=evidence_chunks,
            project_id=project_id,
        )
        raw_result = self.llm_client.score_json(prompt)
        return normalize_semantic_score_result(
            item=item,
            raw_result=raw_result,
            max_score=item.max_score,
        )


def normalize_semantic_score_result(*, item, raw_result: dict[str, Any], max_score: float) -> SemanticScoreResult:
    raw_score = raw_result.get("score", 0.0)
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        score = 0.0
    score = max(0.0, min(score, max_score))

    raw_confidence = raw_result.get("confidence", 0.0)
    try:
        confidence = float(raw_confidence)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(confidence, 1.0))

    decision = str(raw_result.get("decision", "insufficient_evidence"))
    reasoning = str(raw_result.get("reasoning", "")).strip()
    manual_review_required = bool(raw_result.get("manual_review_required", confidence < 0.5))
    matched_evidence_spans = raw_result.get("matched_evidence_spans") or []
    if not isinstance(matched_evidence_spans, list):
        matched_evidence_spans = []

    return SemanticScoreResult(
        item_id=item.item_id,
        item_name=item.item_name,
        decision_mode=item.decision_mode,
        score=score,
        max_score=max_score,
        decision=decision,
        reasoning=reasoning,
        confidence=confidence,
        matched_evidence_spans=matched_evidence_spans,
        manual_review_required=manual_review_required,
        raw_model_output=raw_result,
    )
