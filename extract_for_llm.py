import pdfplumber
import pandas as pd

def extract_scoring_to_markdown(pdf_path, output_md, pages_range):
    """
    专门提取评分标准页，保存为干净的 Markdown 格式
    """
    all_content = []

    with pdfplumber.open(pdf_path) as pdf:
        for p_idx in pages_range:
            page = pdf.pages[p_idx]
            print(f"正在处理第 {p_idx + 1} 页...")

            # 1. 提取文字
            text = page.extract_text()
            if text:
                all_content.append(f"### 第 {p_idx + 1} 页原始文本\n{text}\n")

            # 2. 提取表格并转化为 Markdown
            tables = page.extract_tables()
            for i, table in enumerate(tables):
                # 过滤掉全空的行或列
                df = pd.DataFrame(table).dropna(how='all').dropna(axis=1, how='all')
                if not df.empty:
                    all_content.append(f"#### 表格 {i+1}\n")
                    all_content.append(df.to_markdown(index=False))
                    all_content.append("\n")

    with open(output_md, "w", encoding="utf-8") as f:
        f.write("# 评分标准提取结果\n\n")
        f.write("\n".join(all_content))
    print(f"提取完成！Markdown 已保存至: {output_md}")

if __name__ == "__main__":
    pdf_file = "招标文件正文.pdf"
    output_file = "scoring_criteria_cleaned.md"
    # 第 42 到 59 页 (0-indexed: 41 to 59)
    target_pages = range(41, 59)
    extract_scoring_to_markdown(pdf_file, output_file, target_pages)
