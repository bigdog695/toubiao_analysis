from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BUSINESS_ITEM_IDS = {
    "score_pm_qualification",
    "score_technical_lead_qualification",
    "score_other_key_personnel",
    "score_pm_experience",
    "score_safety_civilization_award",
}

TECHNICAL_ITEM_IDS = {
    "score_equipment_plan",
    "score_labor_plan",
    "score_quality_measures",
    "score_safety_measures",
    "score_schedule_measures",
    "score_civilized_construction",
    "score_site_layout",
    "score_key_difficulties",
}

TECHNICAL_PENALTY_IDS = {
    "score_technical_page_penalty",
}


def load_pipeline_report(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_demo_payload(pipeline_report: dict[str, Any]) -> dict[str, Any]:
    ingest_report = pipeline_report.get("ingest_report") or {}
    score_report = pipeline_report.get("score_report") or {}
    semantic_results = score_report.get("semantic_scoring_results") or []
    rule_based_results = score_report.get("rule_based_results") or []
    price_result = score_report.get("price_result")

    normalized_items = [_normalize_semantic_result(item) for item in semantic_results]
    normalized_items.extend(_normalize_empty_result(item) for item in rule_based_results)

    business_scoring = [item for item in normalized_items if item["item_id"] in BUSINESS_ITEM_IDS]
    technical_scoring = [item for item in normalized_items if item["item_id"] in TECHNICAL_ITEM_IDS]
    technical_penalty = [item for item in normalized_items if item["item_id"] in TECHNICAL_PENALTY_IDS]
    price_scoring = _normalize_empty_result(price_result) if price_result else _empty_price_scoring()

    technical_score_before_penalty = round(sum(_safe_number(item.get("score")) for item in technical_scoring), 3)
    technical_penalty_score = round(sum(_safe_number(item.get("score")) for item in technical_penalty), 3)
    business_score = round(sum(_safe_number(item.get("score")) for item in business_scoring), 3)
    technical_score_final = round(technical_score_before_penalty + technical_penalty_score, 3)
    price_score = round(_safe_number(price_scoring.get("score")), 3)
    total_score = round(business_score + technical_score_final + price_score, 3)
    manual_review_items = [
        item["item_name"]
        for item in business_scoring + technical_scoring + technical_penalty + [price_scoring]
        if item.get("manual_review_required")
    ]

    return {
        "bid_file_name": "sample_toubiao_files",
        "bidder_name": "【待补充】",
        "project_name": "【待补充】",
        "tender_model_status": "已预载",
        "check_result": {
            "file_structure_check": _build_file_structure_check(ingest_report),
            "format_and_manual_review": [
                {
                    "name": "签字盖章检查",
                    "status": "待实现",
                    "detail": "规则引擎未接入，需人工复核。",
                },
                {
                    "name": "关键页格式检查",
                    "status": "待实现",
                    "detail": "规则引擎未接入，需人工复核。",
                },
                {
                    "name": "施工组织设计页数检查",
                    "status": "待实现",
                    "detail": "规则引擎未接入，需后续实现。",
                },
            ],
        },
        "qualification_check": [
            {
                "name": item["item_name"],
                "status": "待实现",
                "evidence": item["reason"],
            }
            for item in business_scoring
            if item["item_id"] in {"score_pm_qualification", "score_technical_lead_qualification", "score_other_key_personnel"}
        ],
        "business_scoring": [_strip_item_id(item) for item in business_scoring],
        "technical_scoring": [_strip_item_id(item) for item in technical_scoring],
        "technical_penalty": [_strip_item_id(item) for item in technical_penalty],
        "price_scoring": _strip_item_id(price_scoring),
        "score_summary": {
            "qualification_result": "待实现",
            "business_score": business_score,
            "technical_score_before_penalty": technical_score_before_penalty,
            "technical_penalty": technical_penalty_score,
            "technical_score_final": technical_score_final,
            "price_score": price_score,
            "total_score": total_score,
            "manual_review_items": manual_review_items,
        },
    }


def _build_file_structure_check(ingest_report: dict[str, Any]) -> list[dict[str, str]]:
    documents = ingest_report.get("documents") or []
    doc_types = {doc.get("doc_type") for doc in documents}
    return [
        {
            "name": "商务文件",
            "status": "通过" if {"other_performance_proof", "personnel_certificates", "project_org_chart"} & doc_types else "待确认",
            "detail": "已按 doc_type 建库。" if doc_types else "未发现文档。",
        },
        {
            "name": "技术文件",
            "status": "通过" if "construction_plan" in doc_types else "待确认",
            "detail": "已按 construction_plan 建库。" if "construction_plan" in doc_types else "未发现技术文件。",
        },
        {
            "name": "报价文件",
            "status": "通过" if "price_file" in doc_types else "待确认",
            "detail": "已按 price_file 建库。" if "price_file" in doc_types else "未发现报价文件。",
        },
        {
            "name": "资格审查资料",
            "status": "通过" if "personnel_certificates" in doc_types else "待确认",
            "detail": "已按 personnel_certificates 建库。" if "personnel_certificates" in doc_types else "未发现资格资料。",
        },
    ]


def _normalize_semantic_result(item: dict[str, Any]) -> dict[str, Any]:
    evidence = [
        f"{ev.get('source_file', 'unknown')} p.{ev.get('page_start', '?')}: {ev.get('quote', '')}"
        for ev in item.get("matched_evidence_spans", [])
    ]
    return {
        "item_id": item.get("item_id"),
        "item_name": item.get("item_name", ""),
        "max_score": _safe_number(item.get("max_score")),
        "score": _safe_number(item.get("score")),
        "result": item.get("decision", ""),
        "confidence": _safe_number(item.get("confidence")),
        "evidence": evidence,
        "reason": item.get("reasoning", ""),
        "manual_review_required": bool(item.get("manual_review_required")),
    }


def _normalize_empty_result(item: dict[str, Any] | None) -> dict[str, Any]:
    if not item:
        return _empty_price_scoring()
    return {
        "item_id": item.get("item_id"),
        "item_name": item.get("item_name", ""),
        "max_score": 0.0,
        "score": _safe_number(item.get("score")),
        "result": item.get("result", ""),
        "confidence": 0.0,
        "evidence": item.get("evidence", []),
        "reason": item.get("reason", ""),
        "manual_review_required": True,
    }


def _empty_price_scoring() -> dict[str, Any]:
    return {
        "item_id": "score_price",
        "item_name": "报价评分",
        "max_score": 80.0,
        "score": 0.0,
        "result": "",
        "confidence": 0.0,
        "evidence": [],
        "reason": "",
        "manual_review_required": True,
    }


def _safe_number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _strip_item_id(item: dict[str, Any]) -> dict[str, Any]:
    payload = dict(item)
    payload.pop("item_id", None)
    return payload
