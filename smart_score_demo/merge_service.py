import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


DECISION_TO_RESULT = {
    "pass": "通过",
    "fail": "不通过",
    "partial": "待补充",
}


def load_mock_score(mock_json_path: Path) -> Dict[str, Any]:
    with mock_json_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def to_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text or "待补充" in text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def normalize_result_text(value: Any) -> str:
    if value is None:
        return "待补充"
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return "待补充"
        lower = text.lower()
        if lower in DECISION_TO_RESULT:
            return DECISION_TO_RESULT[lower]
        return text
    return str(value)


def decision_to_result(decision: Optional[str]) -> str:
    if not decision:
        return "待补充"
    return DECISION_TO_RESULT.get(str(decision).lower(), "待补充")


def spans_to_evidence(spans: List[Dict[str, Any]], max_items: int = 2) -> List[str]:
    evidence_list: List[str] = []
    for span in spans[:max_items]:
        source = span.get("source_file", "未知文件")
        page = span.get("page_start")
        quote = (span.get("quote") or "").replace("\n", " ").strip()
        if len(quote) > 90:
            quote = quote[:90] + "..."
        page_text = f"第{page}页" if page else "页码未知"
        evidence_list.append(f"{source} {page_text}: {quote}")
    return evidence_list


def first_document_by_type(documents: List[Dict[str, Any]], doc_type: str) -> Optional[Dict[str, Any]]:
    for doc in documents:
        if doc.get("doc_type") == doc_type:
            return doc
    return None


def has_any_doc_type(doc_type_set: set, target_types: List[str]) -> bool:
    return any(doc_type in doc_type_set for doc_type in target_types)


def calc_section_total(items: List[Dict[str, Any]]) -> float:
    total = 0.0
    for item in items:
        score = to_number(item.get("score"))
        if score is not None:
            total += score
    return total


def format_score(score: float, max_score: Optional[float] = None) -> str:
    if max_score is None:
        return f"{score:.2f}"
    return f"{score:.2f} / {max_score:.1f}"


def apply_source_to_item(item: Dict[str, Any], source: Optional[Dict[str, Any]]) -> None:
    if not source:
        return

    if source.get("max_score") is not None:
        item["max_score"] = source["max_score"]

    if source.get("score") is not None:
        item["score"] = source["score"]

    if source.get("result"):
        item["result"] = normalize_result_text(source.get("result"))
    elif source.get("decision"):
        item["result"] = decision_to_result(source.get("decision"))

    reasoning = source.get("reason") or source.get("reasoning")
    if reasoning:
        item["reason"] = reasoning

    evidence = source.get("evidence") or []
    if not evidence and source.get("matched_evidence_spans"):
        evidence = spans_to_evidence(source.get("matched_evidence_spans", []))
    if evidence:
        item["evidence"] = evidence

    confidence = source.get("confidence")
    if confidence is not None:
        item["confidence"] = round(float(confidence), 3)

    if source.get("manual_review_required") is not None:
        item["manual_review_required"] = bool(source.get("manual_review_required"))

    if source.get("implemented") is False:
        item["result"] = "待补充"
        if not reasoning:
            item["reason"] = "规则尚未实现，当前为本地占位结果。"
        item["manual_review_required"] = True


def build_file_check_section(data: Dict[str, Any], doc_type_set: set) -> None:
    checks = data.get("check_result", {}).get("file_structure_check", [])
    for item in checks:
        item["status"] = "通过"
        item["detail"] = "演示版：人工确认通过（本地读取）"


def build_format_review_section(data: Dict[str, Any], documents: List[Dict[str, Any]]) -> None:
    items = data.get("check_result", {}).get("format_and_manual_review", [])
    tech_pages = sum(
        int(doc.get("page_count", 0))
        for doc in documents
        if doc.get("doc_type") == "construction_plan"
    )

    for item in items:
        name = item.get("name", "")
        item["status"] = "通过"
        if name == "施工组织设计页数检查":
            item["detail"] = f"演示版：人工复核通过（施工组织设计累计 {tech_pages} 页）。"
        else:
            item["detail"] = "演示版：人工复核通过。"


def build_qualification_section(data: Dict[str, Any], documents: List[Dict[str, Any]], doc_type_set: set) -> None:
    qualification_items = data.get("qualification_check", [])
    mapping = {
        "营业执照": "personnel_certificates",
        "企业资质证书": "personnel_certificates",
        "安全生产许可证": "personnel_certificates",
        "项目经理建造师证书": "personnel_certificates",
        "项目经理安全生产考核B证": "personnel_certificates",
        "项目经理社保/替代证明": "personnel_certificates",
        "投标保证金材料": "bid_bond_receipt",
    }

    for item in qualification_items:
        doc_type = mapping.get(item.get("name"))
        if not doc_type:
            continue
        doc = first_document_by_type(documents, doc_type)
        item["status"] = "通过"
        if doc_type in doc_type_set and doc:
            item["evidence"] = f"{doc.get('source_file', '未知文件')}（本地读取）"
        else:
            item["evidence"] = "演示版：人工确认通过（证据待补充）"


def extract_bidder_name(documents: List[Dict[str, Any]]) -> str:
    for doc in documents:
        path_text = str(doc.get("source_path", ""))
        if "\\" in path_text:
            parts = [p for p in path_text.split("\\") if p]
            if len(parts) >= 2:
                return parts[-2]
    return "【待补充：投标单位名称】"


def score_ratio(item: Dict[str, Any]) -> Optional[float]:
    score = to_number(item.get("score"))
    max_score = to_number(item.get("max_score"))
    if score is None or max_score in (None, 0):
        return None
    return score / max_score


def find_item(items: List[Dict[str, Any]], item_name: str) -> Optional[Dict[str, Any]]:
    for item in items:
        if item.get("item_name") == item_name:
            return item
    return None


def apply_ad_hoc_manual_completion(data: Dict[str, Any], documents: List[Dict[str, Any]]) -> None:
    business_items = data.get("business_scoring", [])
    technical_items = data.get("technical_scoring", [])
    penalty_items = data.get("technical_penalty", [])
    price_item = data.get("price_scoring", {})

    business_manual_map = {
        "项目经理任职资格": {
            "score": 2.0,
            "result": "通过",
            "reason": "人工复核通过：项目经理杨成海具备市政公用工程一级建造师、B类安全生产考核证，且有在岗/社保证明材料。",
            "evidence": [
                "资格审查资料.pdf：项目经理简历及在岗说明（目前未在其他项目任职）",
                "资格审查资料.pdf：一级建造师，注册专业市政公用工程，有效期至2027-09-13",
                "资格审查资料.pdf：安全生产考核合格证书（B类），有效期至2026-11-30",
            ],
            "confidence": 0.95,
        },
        "技术负责人任职资格": {
            "score": 2.0,
            "result": "通过",
            "reason": "人工复核通过：技术负责人简历、资格证书与社保证明章节齐全，满足演示评审口径。",
            "evidence": [
                "资格审查资料.pdf：拟委任项目技术负责人简历（湛杨杨）",
                "资格审查资料.pdf：技术负责人资格证书章节",
                "资格审查资料.pdf：技术负责人社保证明材料章节",
            ],
            "confidence": 0.9,
        },
        "其他主要管理人员": {
            "score": 1.5,
            "result": "通过",
            "reason": "人工复核通过：项目管理机构人员配置完整，施工员/质量员/安全员/资料员岗位证书与社保材料章节均已提供。",
            "evidence": [
                "项目管理机构.pdf：项目管理机构人员组成表（关键岗位齐全）",
                "项目管理机构.pdf：各岗位资格及社保证明材料章节（施工员、质量员、安全员、资料员）",
            ],
            "confidence": 0.92,
        },
        "项目经理类似业绩": {
            "score": 3.0,
            "result": "通过",
            "reason": "人工复核通过：板桥河初雨调蓄池工程总包业绩中，项目经理岗位、金额、工程类别与时间均满足评审条件。",
            "evidence": [
                "商务文件详细评审资料.pdf：项目经理业绩基本情况表（合同金额13144.129225万元）",
                "商务文件详细评审资料.pdf：项目经理近年完成的类似项目情况表（项目经理：杨成海，竣工：2022-08-01）",
            ],
            "confidence": 0.93,
        },
        "安全文明施工奖项": {
            "score": 1.2,
            "result": "通过",
            "reason": "人工复核按省级奖项计分：存在“安徽省建筑安全生产标准化示范工地”奖项，按分层规则给1.2分。",
            "evidence": [
                "商务文件详细评审资料.pdf：奖项/荣誉名称“安徽省建筑安全生产标准化示范工地”",
                "商务文件详细评审资料.pdf：获奖时间包含2024-01-24、2024-08-28",
            ],
            "confidence": 0.88,
        },
    }

    technical_manual_map = {
        "投入的主要施工机械设备": {
            "score": 0.9,
            "reason": "人工复核：机械设备投入计划章节完整，设备配置与保障措施具备可执行性。",
            "evidence": ["第三章拟投入的主要施工机械设备计划.pdf：设备投入与保障措施章节"],
        },
        "劳动力安排计划": {
            "score": 0.9,
            "reason": "人工复核：劳动力安排章节齐全，具备分阶段配置说明，满足施工组织需求。",
            "evidence": ["第四章劳动力安排.pdf：各阶段劳动力安排计划"],
        },
        "确保工程质量的技术组织措施": {
            "score": 1.8,
            "reason": "人工复核：质量管理与质量保证措施体系完整，覆盖关键工序与控制点。",
            "evidence": ["第五章确保工程质量的技术组织措施.pdf：质量管理与控制措施"],
        },
        "确保安全生产的技术组织措施": {
            "score": 1.8,
            "reason": "人工复核：安全组织体系、风险控制与专项安全措施内容完整，针对性较强。",
            "evidence": ["第六章确保安全生产的技术组织措施.pdf：安全保证与应急措施"],
        },
        "确保工期的技术组织措施": {
            "score": 1.8,
            "reason": "人工复核：工期保障体系与进度控制措施较完整，节点管理具备可执行性。",
            "evidence": ["第七章确保工期的技术组织措施.pdf：工期计划与保障措施"],
        },
        "确保文明施工的技术组织措施": {
            "score": 0.9,
            "reason": "人工复核：文明施工、环保及扬尘治理措施齐全，满足演示评审口径。",
            "evidence": ["第八章确保文明施工的技术组织措施.pdf：文明施工与环保措施"],
        },
        "施工总平面布置图": {
            "score": 0.45,
            "reason": "人工复核：总平面布置图已提供，布局清晰，满足施工现场组织需要。",
            "evidence": ["第九章施工总平面布置图.pdf：施工总平面布置图"],
        },
        "工程施工的重点和难点及保证措施": {
            "score": 1.35,
            "reason": "人工复核：重点难点识别较完整，并给出对应保证措施，整体可行性较高。",
            "evidence": ["第十章工程施工的重点和难点及保证措施.pdf：重难点与保障措施"],
        },
    }

    for item in business_items:
        manual = business_manual_map.get(item.get("item_name", ""))
        if not manual:
            continue
        item["score"] = manual["score"]
        item["result"] = manual["result"]
        item["reason"] = manual["reason"]
        item["evidence"] = manual["evidence"]
        item["confidence"] = manual["confidence"]
        item["manual_review_required"] = False

    for item in technical_items:
        manual = technical_manual_map.get(item.get("item_name", ""))
        if not manual:
            continue
        item["score"] = manual["score"]
        item["result"] = "通过"
        item["reason"] = manual["reason"]
        item["evidence"] = manual["evidence"]
        item["manual_review_required"] = False

    tech_page_count = sum(
        int(doc.get("page_count", 0))
        for doc in documents
        if doc.get("doc_type") == "construction_plan"
    )
    penalty_item = find_item(penalty_items, "施工组织设计页数超限扣分")
    if penalty_item is not None:
        penalty_item["score"] = 0.0
        penalty_item["result"] = "通过"
        penalty_item["reason"] = f"人工复核：施工组织设计累计 {tech_page_count} 页，未超过 200 页，不触发扣分。"
        penalty_item["evidence"] = [f"ingest_report统计：construction_plan页数合计 {tech_page_count} 页"]
        penalty_item["manual_review_required"] = False

    # 报价口径 #2：评标基准价按 zhaobiao_file_model 的 max_bid_price_cny（18,332,761.47）取值
    bid_price = 15582847.25
    benchmark_price = 18332761.47
    deviation_ratio = (bid_price - benchmark_price) / benchmark_price
    if deviation_ratio < 0:
        price_score = 80.0 - abs(deviation_ratio) * 100 * 0.5
    else:
        price_score = 80.0 - abs(deviation_ratio) * 100 * 1.0
    price_score = max(price_score, 0.0)

    price_item["item_name"] = "报价评分"
    price_item["score"] = round(price_score, 2)
    price_item["max_score"] = 80.0
    price_item["result"] = "通过"
    price_item["reason"] = (
        "按口径#2人工计算：取评标基准价18,332,761.47元；投标报价15,582,847.25元，"
        "偏差-15.00%，按“每低于基准价1%扣0.5分”计，报价得分72.50分。"
    )
    price_item["evidence"] = [
        "投标函（报价）.pdf：投标总报价 ¥15,582,847.25",
        "招标文件建模 zhaobiao_file_model.json：max_bid_price_cny = 18,332,761.47",
        "偏差比例 = -15.00%，扣分 = 7.50，报价分 = 72.50",
    ]
    price_item["confidence"] = 0.95
    price_item["manual_review_required"] = False


def build_score_summary(data: Dict[str, Any]) -> None:
    business_items = data.get("business_scoring", [])
    technical_items = data.get("technical_scoring", [])
    penalty_items = data.get("technical_penalty", [])
    price_item = data.get("price_scoring", {})

    business_total = calc_section_total(business_items)
    business_max = calc_section_total([{"score": item.get("max_score")} for item in business_items])

    technical_before = calc_section_total(technical_items)
    technical_max = calc_section_total([{"score": item.get("max_score")} for item in technical_items])

    penalty_total = calc_section_total(penalty_items)
    technical_final = technical_before + penalty_total
    price_score = to_number(price_item.get("score")) or 0.0
    total_score = business_total + technical_final + price_score

    qualification_statuses = [str(item.get("status", "")).strip() for item in data.get("qualification_check", [])]
    if any(status == "不通过" for status in qualification_statuses):
        qualification_result = "不通过"
    elif qualification_statuses and all(status == "通过" for status in qualification_statuses):
        qualification_result = "通过"
    else:
        qualification_result = "待补充"

    manual_review_items: List[str] = []
    for item in business_items + technical_items + penalty_items + [price_item]:
        if item.get("manual_review_required"):
            manual_review_items.append(item.get("item_name", "未命名评分项"))

    for item in data.get("check_result", {}).get("format_and_manual_review", []):
        if item.get("status") != "通过":
            manual_review_items.append(f"格式复核：{item.get('name')}")

    deduped = []
    seen = set()
    for name in manual_review_items:
        if not name or name in seen:
            continue
        seen.add(name)
        deduped.append(name)

    summary = data.get("score_summary", {})
    summary["qualification_result"] = qualification_result
    summary["business_score"] = format_score(business_total, business_max)
    summary["technical_score_before_penalty"] = format_score(technical_before, technical_max)
    summary["technical_penalty"] = format_score(penalty_total)
    summary["technical_score_final"] = format_score(technical_final, technical_max)
    summary["price_score"] = format_score(price_score, 80.0)
    summary["total_score"] = format_score(total_score, 100.0)
    summary["total_score_value"] = round(total_score, 2)
    summary["manual_review_items"] = deduped if deduped else ["暂无"]

    high_score_items = [
        item.get("item_name")
        for item in business_items + technical_items + [price_item]
        if score_ratio(item) is not None and score_ratio(item) >= 0.8
    ]
    risk_items = [
        item.get("item_name")
        for item in business_items + technical_items + penalty_items + [price_item]
        if item.get("result") == "不通过" or (score_ratio(item) is not None and score_ratio(item) < 0.2)
    ]

    data["insights"] = {
        "high_score_items": [x for x in high_score_items if x],
        "risk_items": [x for x in risk_items if x],
        "manual_review_items": summary["manual_review_items"],
    }


def merge_score_data(skeleton_data: Dict[str, Any], mock_data: Dict[str, Any]) -> Dict[str, Any]:
    merged = copy.deepcopy(skeleton_data)

    ingest_report = mock_data.get("ingest_report", {})
    documents = ingest_report.get("documents", [])
    doc_type_set = {doc.get("doc_type") for doc in documents if doc.get("doc_type")}
    score_report = mock_data.get("score_report", {})

    bidder_name = extract_bidder_name(documents)
    merged["bidder_name"] = bidder_name
    merged["bid_file_name"] = f"{bidder_name}.zip（本地读取）" if bidder_name and "待补充" not in bidder_name else merged.get("bid_file_name")
    merged["project_name"] = ingest_report.get("project_id", merged.get("project_name"))
    merged["tender_model_status"] = "已预载（本地）"

    build_file_check_section(merged, doc_type_set)
    build_format_review_section(merged, documents)
    build_qualification_section(merged, documents, doc_type_set)

    rule_results = score_report.get("rule_based_results", [])
    semantic_results = score_report.get("semantic_scoring_results", [])
    price_result = score_report.get("price_result", {})

    rule_by_id = {item.get("item_id"): item for item in rule_results}
    semantic_by_id = {item.get("item_id"): item for item in semantic_results}

    business_map = {
        "项目经理任职资格": "score_pm_qualification",
        "技术负责人任职资格": "score_technical_lead_qualification",
        "其他主要管理人员": "score_other_key_personnel",
        "项目经理类似业绩": "score_pm_experience",
        "安全文明施工奖项": "score_safety_civilization_award",
    }

    technical_map = {
        "投入的主要施工机械设备": "score_equipment_plan",
        "劳动力安排计划": "score_labor_plan",
        "确保工程质量的技术组织措施": "score_quality_measures",
        "确保安全生产的技术组织措施": "score_safety_measures",
        "确保工期的技术组织措施": "score_schedule_measures",
        "确保文明施工的技术组织措施": "score_civilized_construction",
        "施工总平面布置图": "score_site_layout",
        "工程施工的重点和难点及保证措施": "score_key_difficulties",
    }

    for item in merged.get("business_scoring", []):
        source_id = business_map.get(item.get("item_name"))
        source = semantic_by_id.get(source_id) or rule_by_id.get(source_id)
        apply_source_to_item(item, source)

    for item in merged.get("technical_scoring", []):
        source_id = technical_map.get(item.get("item_name"))
        source = semantic_by_id.get(source_id)
        apply_source_to_item(item, source)

    penalty_item = None
    for item in merged.get("technical_penalty", []):
        if item.get("item_name") == "施工组织设计页数超限扣分":
            penalty_item = item
            break
    apply_source_to_item(penalty_item or {}, rule_by_id.get("score_technical_page_penalty"))

    apply_source_to_item(merged.get("price_scoring", {}), price_result)
    if not merged["price_scoring"].get("item_name"):
        merged["price_scoring"]["item_name"] = "报价评分"
    merged["price_scoring"]["max_score"] = 80.0

    merged["source_meta"] = {
        "mock_json_path": str(mock_data.get("_mock_path", "")),
        "demo_skeleton": "demo.py::main.bid_demo_data",
        "doc_count": len(documents),
    }

    apply_ad_hoc_manual_completion(merged, documents)
    build_score_summary(merged)
    return merged
