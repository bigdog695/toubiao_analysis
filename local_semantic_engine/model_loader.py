from __future__ import annotations

import json
from pathlib import Path

from .models import SemanticScoringItem


SEMANTIC_DECISION_MODES = {
    "hybrid_rule_rag",
    "rag_llm_scoring",
    "rag_llm_plus_manual_review",
}


def load_scoring_model(model_path: str | Path) -> dict:
    path = Path(model_path)
    return json.loads(path.read_text(encoding="utf-8"))


def load_semantic_scoring_items(model_path: str | Path) -> list[SemanticScoringItem]:
    payload = load_scoring_model(model_path)
    items = payload.get("scoring_model", {}).get("scoring_items", [])
    result: list[SemanticScoringItem] = []
    for item in items:
        decision_mode = item.get("decision_mode", "")
        if decision_mode not in SEMANTIC_DECISION_MODES:
            continue
        result.append(
            SemanticScoringItem(
                item_id=item["item_id"],
                item_name=item["item_name"],
                decision_mode=decision_mode,
                bucket_code=item.get("bucket_code", ""),
                category=item.get("category", ""),
                subcategory=item.get("subcategory", ""),
                max_score=float(item.get("max_score", 0.0)),
                required_doc_types=list(item.get("required_doc_types", [])),
                extraction_targets=list(item.get("extraction_targets", [])),
                retrieval_hints=dict(item.get("retrieval_hints", {})),
                score_logic=dict(item.get("score_logic", {})),
                llm_task=dict(item.get("llm_task", {})),
                raw_item=item,
            )
        )
    return result
