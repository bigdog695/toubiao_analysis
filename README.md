# 招标文件评分标准提取工具 - 使用说明

## 简介

这套工具用于从招标文件PDF中自动提取评分标准，并输出为结构化的JSON格式。

## 文件说明

### 1. `extract_scoring_v3.py` (推荐使用)
**最新的专业版提取工具**，功能最完善。

#### 功能特性
- ✅ 自动提取PDF指定页码范围的内容
- ✅ 解析总体分值构成（技术文件、商务文件、报价文件）
- ✅ 提取详细评审标准表格
- ✅ 识别初步评审标准类型
- ✅ 提取报价计算规则
- ✅ 生成JSON结构化数据
- ✅ 生成人类可读的摘要文件

#### 使用方法
```bash
python3 extract_scoring_v3.py <PDF文件路径> <起始页码> <结束页码> -o <输出文件.json>
```

#### 示例
```bash
# 提取招标文件正文.pdf的42-59页评分标准
python3 extract_scoring_v3.py "招标文件正文.pdf" 42 59 -o scoring_result.json
```

#### 输出文件
- `scoring_result.json` - 结构化的JSON数据
- `scoring_result_summary.txt` - 人类可读的摘要文件

---

### 2. `extract_scoring_criteria_v2.py` (增强版)
中级版本，提供了更多自定义选项。

#### 使用方法
```bash
python3 extract_scoring_criteria_v2.py <PDF文件> <起始页码> <结束页码> -o <输出文件.json>

# 简单模式（仅提取原始文本）
python3 extract_scoring_criteria_v2.py <PDF文件> <起始页码> <结束页码> -o output.json --simple
```

---

### 3. `extract_scoring_criteria.py` (基础版)
最初的版本，功能较简单。

#### 使用方法
```bash
python3 extract_scoring_criteria.py <PDF文件> <起始页码> <结束页码> -o <输出文件.json>
```

---

## 依赖安装

```bash
pip install PyPDF2
```

或使用requirements.txt:
```bash
pip install -r requirements.txt
```

---

## JSON输出格式说明

### 完整结构

```json
{
  "source_file": "招标文件正文.pdf",
  "extraction_time": "2026-01-18T18:51:48.232536",
  "page_range": "42-59",

  "scoring_structure": {
    "technical_file": 10,
    "business_file": 10,
    "pricing_file": 80,
    "total": 100
  },

  "preliminary_criteria": {
    "types": ["形式评审", "资格评审", "响应性评审"]
  },

  "detailed_criteria": [
    {
      "section": "技术文件",
      "category": "拟投入的主",
      "evaluation_factor": "要物资计划",
      "max_score": 0.5,
      "evaluation_standard": "投入的施工材料有详细计划...",
      "id": "技术文件_1"
    }
  ],

  "pricing_rules": {
    "has_pricing_calculation": true,
    "c_value_info": "0.975、0.980、0.985..."
  },

  "statistics": {
    "total_criteria_items": 11,
    "total_score": 92.5,
    "sections": ["技术文件"]
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `source_file` | string | 来源PDF文件路径 |
| `extraction_time` | string | 提取时间 (ISO 8601格式) |
| `page_range` | string | 提取的页码范围 |
| `scoring_structure` | object | 总体分值构成 |
| `preliminary_criteria` | object | 初步评审标准 |
| `detailed_criteria` | array | 详细评审标准列表 |
| `pricing_rules` | object | 报价计算规则 |
| `statistics` | object | 统计信息 |

#### detailed_criteria 数组项说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `section` | string | 所属章节（技术文件/商务文件/报价文件） |
| `category` | string | 二级分类 |
| `evaluation_factor` | string | 评分因素名称 |
| `max_score` | number | 该项最高分值 |
| `evaluation_standard` | string | 评分标准描述 |
| `id` | string | 唯一标识符 |

---

## 实际使用案例

### 案例1：提取评分标准
```bash
python3 extract_scoring_v3.py "招标文件正文.pdf" 42 59 -o result.json
```

**输出：**
- `result.json` - 包含11个评分项的JSON文件
- `result_summary.txt` - 可读性强的摘要文件

### 案例2：批量处理多个招标文件
```bash
# 创建批处理脚本
for file in 招标文件*.pdf; do
    python3 extract_scoring_v3.py "$file" 42 59 -o "${file%.pdf}_scoring.json"
done
```

---

## 常见问题

### Q1: PDF文本提取不完整怎么办？
**A:** 某些PDF可能是扫描件或使用了特殊字体，建议：
- 使用OCR工具先转换PDF
- 尝试其他PDF处理库（如pdfplumber）

### Q2: 评分项识别不准确？
**A:** 脚本使用正则表达式匹配，对于特殊格式可能需要调整。可以：
- 检查PDF文本提取质量
- 根据实际格式调整脚本中的正则表达式

### Q3: 如何修改页码范围？
**A:** 直接修改命令行参数中的起始和结束页码即可。

### Q4: 支持哪些PDF格式？
**A:** 支持标准PDF格式，不支持加密PDF。

---

## 后续改进方向

1. **支持更多PDF库**: 添加pdfplumber、pypdf等作为备选
2. **OCR集成**: 对扫描件PDF进行OCR识别
3. **表格结构识别**: 使用机器学习模型识别复杂表格
4. **GUI界面**: 开发图形界面，方便非技术人员使用
5. **模板定制**: 支持不同招标文件格式的模板配置

---

## 技术栈

- Python 3.10+
- PyPDF2: PDF文本提取
- 正则表达式: 文本模式匹配
- JSON: 结构化数据输出

---

## 许可证

MIT License

---

## 更新日志

### v3.0 (2026-01-18)
- ✅ 重构评分项提取算法
- ✅ 改进分类识别准确度
- ✅ 添加人类可读摘要生成
- ✅ 优化JSON结构

### v2.0 (2026-01-18)
- ✅ 添加详细评审标准解析
- ✅ 支持分值构成提取
- ✅ 添加统计信息

### v1.0 (2026-01-18)
- ✅ 基础PDF文本提取
- ✅ 简单评分项识别
