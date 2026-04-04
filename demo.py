# -*- coding: utf-8 -*-

def render_section_title(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def render_kv(label, value):
    print(f"{label}: {value}")


def render_list(title, items):
    print(f"\n{title}")
    for item in items:
        print(f" - {item}")


def render_score_item(item):
    print(f"评分项: {item['item_name']}")
    print(f"  得分: {item['score']} / {item['max_score']}")
    if "result" in item:
        print(f"  结果: {item['result']}")
    if "confidence" in item:
        print(f"  置信度: {item['confidence']}")
    if "reason" in item:
        print(f"  理由: {item['reason']}")
    if "evidence" in item and item["evidence"]:
        print("  证据:")
        for ev in item["evidence"]:
            print(f"    - {ev}")
    print("-" * 60)


def main():
    bid_demo_data = {
        "bid_file_name": "【待补充：投标文件名称】",
        "bidder_name": "【待补充：投标单位名称】",
        "project_name": "【待补充：项目名称】",
        "tender_model_status": "已预载",

        "check_result": {
            "file_structure_check": [
                {
                    "name": "商务文件",
                    "status": "通过",
                    "detail": "已识别到商务文件目录与主体内容"
                },
                {
                    "name": "技术文件",
                    "status": "通过",
                    "detail": "已识别到施工组织设计相关内容"
                },
                {
                    "name": "报价文件",
                    "status": "【待补充】",
                    "detail": "【待补充：是否已识别报价文件】"
                },
                {
                    "name": "资格审查资料",
                    "status": "通过",
                    "detail": "已识别到资格审查资料章节"
                }
            ],
            "format_and_manual_review": [
                {
                    "name": "签字盖章检查",
                    "status": "【待补充】",
                    "detail": "【待补充：人工复核结果】"
                },
                {
                    "name": "关键页格式检查",
                    "status": "【待补充】",
                    "detail": "【待补充：人工复核结果】"
                },
                {
                    "name": "施工组织设计页数检查",
                    "status": "【待补充】",
                    "detail": "【待补充：页数是否超过200页】"
                }
            ]
        },

        "qualification_check": [
            {
                "name": "营业执照",
                "status": "通过",
                "evidence": "【待补充：文件名/页码】"
            },
            {
                "name": "企业资质证书",
                "status": "通过",
                "evidence": "【待补充：市政公用工程施工总承包三级及以上证明】"
            },
            {
                "name": "安全生产许可证",
                "status": "通过",
                "evidence": "【待补充：文件名/页码】"
            },
            {
                "name": "项目经理建造师证书",
                "status": "通过",
                "evidence": "【待补充：文件名/页码】"
            },
            {
                "name": "项目经理安全生产考核B证",
                "status": "通过",
                "evidence": "【待补充：文件名/页码】"
            },
            {
                "name": "项目经理社保/替代证明",
                "status": "【待补充】",
                "evidence": "【待补充：文件名/页码】"
            },
            {
                "name": "投标保证金材料",
                "status": "【待补充】",
                "evidence": "【待补充：保证金形式/金额/凭证】"
            }
        ],

        # 商务评分满分 10.0
        "business_scoring": [
            {
                "item_name": "项目经理任职资格",
                "max_score": 2.0,
                "score": "【待补充】",
                "result": "【待补充：满足/不满足】",
                "evidence": [
                    "【待补充：项目经理证书】",
                    "【待补充：B证】",
                    "【待补充：社保证明】"
                ],
                "reason": "【待补充：规则判断理由】"
            },
            {
                "item_name": "技术负责人任职资格",
                "max_score": 2.0,
                "score": "【待补充】",
                "result": "【待补充：满足/不满足】",
                "evidence": [
                    "【待补充：技术负责人材料】"
                ],
                "reason": "【待补充：规则判断理由】"
            },
            {
                "item_name": "其他主要管理人员",
                "max_score": 1.5,
                "score": "【待补充】",
                "result": "【待补充：满足/不满足】",
                "evidence": [
                    "【待补充：项目管理机构相关材料】"
                ],
                "reason": "【待补充：规则判断理由】"
            },
            {
                "item_name": "项目经理类似业绩",
                "max_score": 3.0,
                "score": "【待补充】",
                "result": "【待补充：满足/不满足】",
                "evidence": [
                    "【待补充：合同金额】",
                    "【待补充：工程类别】",
                    "【待补充：担任岗位】",
                    "【待补充：时间范围】"
                ],
                "reason": "【待补充：规则判断理由】"
            },
            {
                "item_name": "安全文明施工奖项",
                "max_score": 1.5,
                "score": "【待补充】",
                "result": "【待补充：国家级/省级/市级/无】",
                "evidence": [
                    "【待补充：奖项名称】",
                    "【待补充：奖项级别】",
                    "【待补充：对应工程】"
                ],
                "reason": "【待补充：规则判断理由】"
            }
        ],

        # 技术评分满分 10.0
        "technical_scoring": [
            {
                "item_name": "投入的主要施工机械设备",
                "max_score": 1.0,
                "score": "【待补充】",
                "confidence": "【待补充】",
                "evidence": [
                    "【待补充：设备配置片段1】",
                    "【待补充：设备配置片段2】"
                ],
                "reason": "【待补充：LLM评分理由】"
            },
            {
                "item_name": "劳动力安排计划",
                "max_score": 1.0,
                "score": "【待补充】",
                "confidence": "【待补充】",
                "evidence": [
                    "【待补充：劳动力安排片段1】",
                    "【待补充：劳动力安排片段2】"
                ],
                "reason": "【待补充：LLM评分理由】"
            },
            {
                "item_name": "确保工程质量的技术组织措施",
                "max_score": 2.0,
                "score": "【待补充】",
                "confidence": "【待补充】",
                "evidence": [
                    "【待补充：质量措施片段1】",
                    "【待补充：质量措施片段2】"
                ],
                "reason": "【待补充：LLM评分理由】"
            },
            {
                "item_name": "确保安全生产的技术组织措施",
                "max_score": 2.0,
                "score": "【待补充】",
                "confidence": "【待补充】",
                "evidence": [
                    "【待补充：安全措施片段1】",
                    "【待补充：安全措施片段2】"
                ],
                "reason": "【待补充：LLM评分理由】"
            },
            {
                "item_name": "确保工期的技术组织措施",
                "max_score": 2.0,
                "score": "【待补充】",
                "confidence": "【待补充】",
                "evidence": [
                    "【待补充：工期措施片段1】",
                    "【待补充：工期措施片段2】"
                ],
                "reason": "【待补充：LLM评分理由】"
            },
            {
                "item_name": "确保文明施工的技术组织措施",
                "max_score": 1.0,
                "score": "【待补充】",
                "confidence": "【待补充】",
                "evidence": [
                    "【待补充：文明施工/环保/扬尘治理片段】"
                ],
                "reason": "【待补充：LLM评分理由】"
            },
            {
                "item_name": "施工总平面布置图",
                "max_score": 0.5,
                "score": "【待补充】",
                "confidence": "【待补充】",
                "evidence": [
                    "【待补充：平面布置图说明】"
                ],
                "reason": "【待补充：LLM或人工复核理由】"
            },
            {
                "item_name": "工程施工的重点和难点及保证措施",
                "max_score": 1.5,
                "score": "【待补充】",
                "confidence": "【待补充】",
                "evidence": [
                    "【待补充：重点难点片段1】",
                    "【待补充：重点难点片段2】"
                ],
                "reason": "【待补充：LLM评分理由】"
            }
        ],

        # 页数超限扣分，属于技术文件格式扣分
        "technical_penalty": [
            {
                "item_name": "施工组织设计页数超限扣分",
                "max_score": -1.0,
                "score": "【待补充：0 或 -1.0】",
                "result": "【待补充：是否超出200页】",
                "evidence": [
                    "【待补充：实际页数】"
                ],
                "reason": "【待补充：规则判断理由】"
            }
        ],

        # 报价评分满分 80.0
        "price_scoring": {
            "item_name": "报价评分",
            "max_score": 80.0,
            "score": "【待补充】",
            "result": "【待补充：规则计算结果】",
            "evidence": [
                "【待补充：投标报价】",
                "【待补充：评标基准价】",
                "【待补充：偏差比例】"
            ],
            "reason": "【待补充：报价评分公式计算说明】"
        },

        "score_summary": {
            "qualification_result": "【待补充：通过/不通过/部分通过】",
            "business_score": "【待补充：满分10.0】",
            "technical_score_before_penalty": "【待补充：满分10.0】",
            "technical_penalty": "【待补充：0 或 -1.0】",
            "technical_score_final": "【待补充：技术实得分】",
            "price_score": "【待补充：满分80.0】",
            "total_score": "【待补充：满分100.0】",
            "manual_review_items": [
                "【待补充：需人工复核项1】",
                "【待补充：需人工复核项2】"
            ]
        }
    }

    render_section_title("投标文件智能检查与辅助评分结果")

    render_kv("投标文件", bid_demo_data["bid_file_name"])
    render_kv("投标单位", bid_demo_data["bidder_name"])
    render_kv("项目名称", bid_demo_data["project_name"])
    render_kv("招标模型状态", bid_demo_data["tender_model_status"])

    render_section_title("一、文件检查结果")
    for item in bid_demo_data["check_result"]["file_structure_check"]:
        print(f"[{item['status']}] {item['name']} -> {item['detail']}")

    render_section_title("二、格式与人工复核结果")
    for item in bid_demo_data["check_result"]["format_and_manual_review"]:
        print(f"[{item['status']}] {item['name']} -> {item['detail']}")

    render_section_title("三、资格与证书核验结果")
    for item in bid_demo_data["qualification_check"]:
        print(f"[{item['status']}] {item['name']}")
        print(f"  证据: {item['evidence']}")

    render_section_title("四、商务评分结果（满分 10.0）")
    for item in bid_demo_data["business_scoring"]:
        render_score_item(item)

    render_section_title("五、技术评分结果（满分 10.0）")
    for item in bid_demo_data["technical_scoring"]:
        render_score_item(item)

    render_section_title("六、技术文件格式扣分")
    for item in bid_demo_data["technical_penalty"]:
        render_score_item(item)

    render_section_title("七、报价评分结果（满分 80.0）")
    render_score_item(bid_demo_data["price_scoring"])

    render_section_title("八、总分汇总（满分 100.0）")
    render_kv("资格核验结论", bid_demo_data["score_summary"]["qualification_result"])
    render_kv("商务评分", bid_demo_data["score_summary"]["business_score"])
    render_kv("技术评分（扣分前）", bid_demo_data["score_summary"]["technical_score_before_penalty"])
    render_kv("技术文件格式扣分", bid_demo_data["score_summary"]["technical_penalty"])
    render_kv("技术评分（最终）", bid_demo_data["score_summary"]["technical_score_final"])
    render_kv("报价评分", bid_demo_data["score_summary"]["price_score"])
    render_kv("总分", bid_demo_data["score_summary"]["total_score"])

    render_list("待人工复核项", bid_demo_data["score_summary"]["manual_review_items"])


if __name__ == "__main__":
    main()