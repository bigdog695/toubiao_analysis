from __future__ import annotations

import json
from pathlib import Path


DEFAULT_DOC_TYPE_KEYWORDS: dict[str, list[str]] = {
    "business_license": ["营业执照"],
    "enterprise_qualification_certificate": ["资质证书", "施工总承包", "市政公用工程"],
    "safety_production_license": ["安全生产许可证"],
    "registered_constructor_certificate": ["注册建造师", "建造师证书"],
    "safety_b_certificate": ["安全生产考核合格证", "B类", "B证"],
    "social_security_record": ["社保证明", "社会保险"],
    "retirement_proof": ["退休证明"],
    "employment_contract": ["聘用合同", "劳动合同"],
    "salary_statement": ["工资流水", "工资发放"],
    "credit_commitment": ["信誉承诺"],
    "joint_venture_agreement": ["联合体协议书"],
    "bid_bond_receipt": ["投标保证金", "保证金回执"],
    "paper_guarantee": ["纸质保函"],
    "electronic_guarantee": ["电子保函"],
    "technical_lead_resume": ["技术负责人简历", "技术负责人"],
    "technical_lead_certificates": ["技术负责人证书"],
    "project_org_chart": ["项目管理机构", "组织机构"],
    "personnel_certificates": ["人员证书", "岗位证书"],
    "performance_contract": ["业绩", "合同金额", "项目经理", "合同协议书"],
    "completion_acceptance_doc": ["竣工验收", "完工证明", "验收证明"],
    "award_certificate": ["奖项", "获奖", "证书"],
    "award_notice": ["获奖通知", "表彰决定"],
    "project_award_proof": ["示范工地", "安全文明施工"],
    "construction_plan": ["施工组织设计", "施工方案", "施工机械设备", "劳动力安排"],
    "site_layout_diagram": ["平面布置图", "施工总平面图"],
    "other_performance_proof": ["业绩证明", "中标通知书"],
}


def load_doc_type_catalog(model_path: str | Path | None = None) -> list[str]:
    if model_path is None:
        return sorted(DEFAULT_DOC_TYPE_KEYWORDS)

    path = Path(model_path)
    if not path.exists():
        return sorted(DEFAULT_DOC_TYPE_KEYWORDS)

    payload = json.loads(path.read_text(encoding="utf-8"))
    catalog = payload.get("api_friendly_views", {}).get("required_docs_catalog", [])
    values = set(DEFAULT_DOC_TYPE_KEYWORDS)
    values.update(value for value in catalog if isinstance(value, str) and value)
    return sorted(values)


def suggest_doc_type(
    source_file: str,
    full_text: str,
    *,
    allowed_doc_types: list[str] | None = None,
) -> tuple[str, str]:
    searchable = f"{source_file}\n{full_text[:8000]}".lower()
    candidates = allowed_doc_types or sorted(DEFAULT_DOC_TYPE_KEYWORDS)

    best_doc_type = "unclassified"
    best_score = 0
    for doc_type in candidates:
        keywords = DEFAULT_DOC_TYPE_KEYWORDS.get(doc_type, [])
        score = sum(1 for keyword in keywords if keyword.lower() in searchable)
        if doc_type in source_file.lower():
            score += 2
        if score > best_score:
            best_doc_type = doc_type
            best_score = score

    if best_score == 0 and candidates:
        if "技术" in source_file or "施工组织设计" in searchable:
            return "construction_plan", "suggested"
        if "奖" in source_file:
            return "award_certificate", "suggested"
        if "合同" in source_file:
            return "performance_contract", "suggested"

    return best_doc_type, "suggested"
